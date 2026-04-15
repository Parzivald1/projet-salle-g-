"""
Moniteur DNS - Récupération et agrégation des logs Unbound
Stockage en RAM uniquement (buffer circulaire 30 min)

Collecte via l'API OPNsense :
  - Requêtes DNS (Unbound)
  - Table ARP (mapping IP → MAC)
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from .opnsense import opnsense

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

POLL_INTERVAL = 15         # Secondes entre chaque poll DNS
ARP_POLL_INTERVAL = 30     # Secondes entre chaque refresh ARP
BUFFER_DURATION = 30       # Minutes de rétention en RAM
STUDENT_NETWORK = "192.168.2."  # Préfixe IP du VLAN 20 (élèves)

# Domaines "infrastructure" à ignorer (CDN, trackers, connectivité, OS, etc.)
IGNORED_DOMAINS = {
    # Vérifications de connectivité
    'connectivitycheck.gstatic.com', 'detectportal.firefox.com',
    'captive.apple.com', 'msftconnecttest.com', 'msftncsi.com',
    'www.msftconnecttest.com', 'dns.msftncsi.com',
    'connectivity-check.ubuntu.com', 'nmcheck.gnome.org',
    # Certificats / révocation
    'ocsp.digicert.com', 'ocsp.pki.goog', 'ocsp.globalsign.com',
    'ocsp.sectigo.com', 'ocsp.entrust.net', 'ocsp.usertrust.com',
    'crl.microsoft.com', 'crl3.digicert.com', 'crl4.digicert.com',
    'crl.globalsign.com', 'crl.pki.goog',
    'x1.c.lencr.org', 'r3.o.lencr.org', 'r10.o.lencr.org',
    'e1.o.lencr.org',
    # NTP
    'time.windows.com', 'time.google.com', 'ntp.ubuntu.com',
    'pool.ntp.org',
    # Télémétrie Windows
    'settings-win.data.microsoft.com', 'v10.events.data.microsoft.com',
    'watson.telemetry.microsoft.com', 'self.events.data.microsoft.com',
    'vortex.data.microsoft.com',
    # Télémétrie / mise à jour divers
    'telemetry.mozilla.org', 'incoming.telemetry.mozilla.org',
    'safebrowsing.googleapis.com', 'safebrowsing.google.com',
    'shavar.services.mozilla.com', 'push.services.mozilla.com',
    'snippets.cdn.mozilla.net', 'location.services.mozilla.com',
    'firefox.settings.services.mozilla.com',
    'contile.services.mozilla.com',
    # DNS racine
    'a.root-servers.net', 'b.root-servers.net', 'c.root-servers.net',
    'd.root-servers.net', 'e.root-servers.net', 'f.root-servers.net',
    'g.root-servers.net', 'h.root-servers.net', 'i.root-servers.net',
    'j.root-servers.net', 'k.root-servers.net', 'l.root-servers.net',
    'm.root-servers.net',
    # Mises à jour système
    'windowsupdate.com', 'update.microsoft.com',
    'download.windowsupdate.com', 'dl.delivery.mp.microsoft.com',
    'au.download.windowsupdate.com',
}

# Suffixes de domaines à toujours ignorer
IGNORED_SUFFIXES = (
    '.arpa', '.local', '.internal', '.localhost',
    '.windowsupdate.com', '.update.microsoft.com',
    '.delivery.mp.microsoft.com',
)

# Mapping sous-domaine → domaine principal (pour l'agrégation)
DOMAIN_ALIASES = {
    'googlevideo.com': 'youtube.com',
    'ytimg.com': 'youtube.com',
    'yt3.ggpht.com': 'youtube.com',
    'youtubei.googleapis.com': 'youtube.com',
    'youtube-ui.l.google.com': 'youtube.com',
    'i.ytimg.com': 'youtube.com',
    'i9.ytimg.com': 'youtube.com',
    'yt3.googleusercontent.com': 'youtube.com',
    'rr1.sn-': 'youtube.com',  # CDN YouTube
    'www.youtube.com': 'youtube.com',
    'm.youtube.com': 'youtube.com',
    'youtu.be': 'youtube.com',
    'play.google.com': 'google.com',
    'clients1.google.com': 'google.com',
    'ssl.gstatic.com': 'google.com',
    'fonts.gstatic.com': 'google.com',
    'fonts.googleapis.com': 'google.com',
    'lh3.googleusercontent.com': 'google.com',
    'www.google.com': 'google.com',
    'www.google.fr': 'google.com',
    'accounts.google.com': 'google.com',
    'docs.google.com': 'google.com',
    'drive.google.com': 'google.com',
    'sheets.google.com': 'google.com',
    'slides.google.com': 'google.com',
    'mail.google.com': 'google.com',
    'googlemail.com': 'google.com',
    'fr.wikipedia.org': 'wikipedia.org',
    'en.wikipedia.org': 'wikipedia.org',
    'upload.wikimedia.org': 'wikipedia.org',
    'maps.wikimedia.org': 'wikipedia.org',
    'login.microsoftonline.com': 'microsoft.com',
    'login.windows.net': 'microsoft.com',
    'login.live.com': 'microsoft.com',
    'outlook.office.com': 'microsoft.com',
    'outlook.office365.com': 'microsoft.com',
    'outlook.live.com': 'microsoft.com',
    'teams.microsoft.com': 'microsoft.com',
    'office.com': 'microsoft.com',
    'office365.com': 'microsoft.com',
    'sharepoint.com': 'microsoft.com',
    'onedrive.com': 'microsoft.com',
    'live.com': 'microsoft.com',
    'microsoftonline.com': 'microsoft.com',
}


def _extract_root_domain(domain):
    """Extrait le domaine racine (TLD+1) pour l'agrégation"""
    if not domain:
        return domain

    domain = domain.lower().rstrip('.')

    # Vérifier d'abord les alias explicites
    if domain in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[domain]

    # Vérifier par suffixe pour les alias partiels
    for alias_key, alias_val in DOMAIN_ALIASES.items():
        if domain.endswith('.' + alias_key):
            return alias_val

    # Extraction classique TLD+1
    parts = domain.split('.')
    if len(parts) <= 2:
        return domain

    # Gérer les TLD composés (co.uk, com.br, etc.)
    if len(parts) >= 3 and parts[-2] in ('co', 'com', 'org', 'net', 'edu', 'gov', 'ac'):
        return '.'.join(parts[-3:])

    return '.'.join(parts[-2:])


def _should_ignore(domain):
    """Vérifie si un domaine doit être ignoré"""
    if not domain:
        return True

    domain = domain.lower().rstrip('.')

    if domain in IGNORED_DOMAINS:
        return True

    for suffix in IGNORED_SUFFIXES:
        if domain.endswith(suffix):
            return True

    return False


# =============================================================================
# Buffer en RAM
# =============================================================================

class DNSBuffer:
    """Buffer circulaire thread-safe pour les logs DNS agrégés"""

    def __init__(self, max_minutes=BUFFER_DURATION):
        self.max_minutes = max_minutes
        self.lock = threading.Lock()

        # Clé: (ip, domaine_racine)
        # Valeur: {count, first_seen, last_seen, blocked, domains_raw, action}
        self.entries = {}

        # Table ARP : IP → MAC
        self.arp_table = {}

        # Stats
        self.total_queries = 0
        self.total_blocked = 0
        self.last_poll = None
        self.last_arp_poll = None
        self.is_running = False

        # Pour le polling incrémental : garder le dernier timestamp vu
        self._last_seen_timestamp = None

    def add_query(self, ip, domain_raw, action, timestamp_str=None):
        """Ajoute une requête DNS au buffer"""
        if _should_ignore(domain_raw):
            return

        root_domain = _extract_root_domain(domain_raw)
        is_blocked = (action == 'Block')
        now = datetime.now()

        with self.lock:
            key = (ip, root_domain)
            if key in self.entries:
                entry = self.entries[key]
                entry['count'] += 1
                entry['last_seen'] = now
                entry['domains_raw'].add(domain_raw)
                if is_blocked:
                    entry['blocked_count'] += 1
            else:
                self.entries[key] = {
                    'count': 1,
                    'first_seen': now,
                    'last_seen': now,
                    'blocked_count': 1 if is_blocked else 0,
                    'domains_raw': {domain_raw},
                }

            self.total_queries += 1
            if is_blocked:
                self.total_blocked += 1

    def update_arp(self, arp_entries):
        """Met à jour la table ARP"""
        with self.lock:
            self.arp_table = {}
            for entry in arp_entries:
                ip = entry.get('ip', '')
                mac = entry.get('mac', '')
                hostname = entry.get('hostname', '')
                if ip.startswith(STUDENT_NETWORK) and mac:
                    self.arp_table[ip] = {
                        'mac': mac.upper(),
                        'hostname': hostname,
                    }
            self.last_arp_poll = datetime.now()

    def cleanup(self):
        """Supprime les entrées plus vieilles que max_minutes"""
        cutoff = datetime.now() - timedelta(minutes=self.max_minutes)
        with self.lock:
            expired_keys = [
                k for k, v in self.entries.items()
                if v['last_seen'] < cutoff
            ]
            for key in expired_keys:
                del self.entries[key]

    def get_snapshot(self):
        """Retourne un snapshot des données pour l'API"""
        with self.lock:
            result = []
            for (ip, domain), entry in self.entries.items():
                arp_info = self.arp_table.get(ip, {})
                result.append({
                    'ip': ip,
                    'mac': arp_info.get('mac', '—'),
                    'hostname': arp_info.get('hostname', ''),
                    'domain': domain,
                    'count': entry['count'],
                    'blocked_count': entry['blocked_count'],
                    'first_seen': entry['first_seen'].strftime('%H:%M:%S'),
                    'last_seen': entry['last_seen'].strftime('%H:%M:%S'),
                    'last_seen_ts': entry['last_seen'].timestamp(),
                    'sub_domains': list(entry['domains_raw'])[:10],
                })

            # Trier par activité la plus récente
            result.sort(key=lambda x: x['last_seen_ts'], reverse=True)

            return {
                'entries': result,
                'stats': {
                    'total_queries': self.total_queries,
                    'total_blocked': self.total_blocked,
                    'active_clients': len(set(
                        k[0] for k in self.entries.keys()
                    )),
                    'unique_domains': len(set(
                        k[1] for k in self.entries.keys()
                    )),
                    'last_poll': self.last_poll.strftime('%H:%M:%S') if self.last_poll else '—',
                    'buffer_minutes': self.max_minutes,
                },
                'is_running': self.is_running,
            }

    def clear(self):
        """Vide le buffer"""
        with self.lock:
            self.entries.clear()
            self.total_queries = 0
            self.total_blocked = 0


# Instance globale
dns_buffer = DNSBuffer()


# =============================================================================
# Thread de polling
# =============================================================================

class DNSPollerThread(threading.Thread):
    """Thread daemon qui poll l'API Unbound et ARP"""

    def __init__(self):
        super().__init__(daemon=True)
        self.name = "dns-poller"
        self._stop_event = threading.Event()
        self._arp_counter = 0

    def run(self):
        logger.info("DNS Poller démarré (interval=%ds, buffer=%dmin)",
                     POLL_INTERVAL, BUFFER_DURATION)
        dns_buffer.is_running = True

        # Premier refresh ARP immédiat
        self._poll_arp()

        while not self._stop_event.is_set():
            try:
                self._poll_dns()
                dns_buffer.last_poll = datetime.now()

                # ARP toutes les ARP_POLL_INTERVAL secondes
                self._arp_counter += POLL_INTERVAL
                if self._arp_counter >= ARP_POLL_INTERVAL:
                    self._poll_arp()
                    self._arp_counter = 0

                # Nettoyage des vieilles entrées
                dns_buffer.cleanup()

            except Exception as e:
                logger.error("Erreur polling DNS: %s", e)

            self._stop_event.wait(POLL_INTERVAL)

        dns_buffer.is_running = False
        logger.info("DNS Poller arrêté")

    def stop(self):
        self._stop_event.set()

    def _poll_dns(self):
        """Récupère les derniers logs Unbound via l'API"""
        try:
            result = opnsense._request('GET', 'unbound/overview/searchQueries')
            if not result['success']:
                logger.warning("Échec récupération logs Unbound: %s",
                               result.get('error', '?'))
                return

            data = result['data']
            rows = data.get('rows', [])

            if not rows:
                return

            # Approche simple : on clear et reconstruit le buffer à chaque poll
            # car l'API renvoie toujours les 1000 dernières requêtes (snapshot)
            dns_buffer.clear()

            for row in rows:
                client_ip = row.get('client', '')

                # Ne garder que les IPs du réseau élèves
                if not client_ip.startswith(STUDENT_NETWORK):
                    continue

                # Nettoyer le domaine (l'API ajoute un '.' final)
                domain = row.get('domain', '').rstrip('.')
                action = row.get('action', 'Pass')

                dns_buffer.add_query(client_ip, domain, action)

        except Exception as e:
            logger.error("Erreur poll DNS: %s", e)

    def _poll_arp(self):
        """Récupère la table ARP depuis OPNsense"""
        try:
            result = opnsense._request('GET', 'diagnostics/interface/getArp')
            if not result['success']:
                logger.warning("Échec récupération ARP: %s",
                               result.get('error', '?'))
                return

            data = result['data']
            # L'API renvoie un tableau directement ou sous une clé
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = data.get('rows', data.get('arp', []))
                if isinstance(entries, dict):
                    entries = list(entries.values())
            else:
                entries = []

            dns_buffer.update_arp(entries)
            logger.debug("Table ARP mise à jour: %d entrées",
                         len(dns_buffer.arp_table))

        except Exception as e:
            logger.error("Erreur poll ARP: %s", e)


# Instance globale du poller
_poller = None


def start_dns_monitor():
    """Démarre le monitoring DNS (un seul poller même avec plusieurs workers)"""
    global _poller
    import fcntl

    # Utiliser un fichier lock pour qu'un seul worker lance le poller
    lock_file = '/tmp/dns_poller.lock'
    try:
        _lock_fd = open(lock_file, 'w')
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # On a le lock → on lance le poller
        if _poller is None or not _poller.is_alive():
            _poller = DNSPollerThread()
            _poller.start()
            logger.info("DNS Monitor lancé (ce worker a le lock)")
    except (IOError, OSError):
        # Un autre worker a déjà le lock → pas de poller ici
        logger.info("DNS Monitor: autre worker actif, pas de poller ici")


def stop_dns_monitor():
    """Arrête le monitoring DNS"""
    global _poller
    if _poller and _poller.is_alive():
        _poller.stop()
        _poller.join(timeout=10)
        _poller = None
        logger.info("DNS Monitor arrêté")
