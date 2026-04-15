"""
Gestion des modes de filtrage, des packs de sites, et des règles firewall.

Modes :
- Total   : Guillotine OFF → tout passe, Unbound bloque les sites interdits
- Partiel : Guillotine ON + règles whitelist → seuls les packs activés passent
- Aucun   : Guillotine ON + APP_WORK uniquement → pas de navigation web
"""

import json
import os
from .opnsense import opnsense
from database.models import get_mode_actif, set_mode_actif

# =============================================================================
# UUIDs des règles firewall
# =============================================================================

RULE_UUIDS = {
    'guillotine': '026819dc-6dd2-44c3-9b74-4a080cdd40a8',
    'dns_local': '574749f0-43c3-4f96-9c04-19077844ba33',
    'whitelist_http': '47c593ce-6e30-4e10-afd5-659eee6b0c49',
    'whitelist_https': '18c43499-75b2-4c37-8979-01dd9bdca86a',
    'app_work': 'f5219c41-0159-471d-bcaa-49f0d4ef9456',
}

ALIAS_UUIDS = {
    'whitelist_partiel': 'e8402a86-3260-4553-9e32-4fb691af47d3',
}

# =============================================================================
# Packs de sites pré-configurés
# =============================================================================

SITE_PACKS = {
    # --- Priorité : toujours actifs, non décochables ---
    'wikipedia': {
        'nom': 'Wikipedia',
        'icone': 'W',
        'logo_domain': 'wikipedia.org',
        'description': 'Encyclopédie en ligne',
        'verrouille': True,
        'domaines': [
            'wikipedia.org', 'fr.wikipedia.org', 'en.wikipedia.org',
            'wikimedia.org', 'mediawiki.org',
        ]
    },
    'easitraining': {
        'nom': 'Easi Training',
        'icone': 'ET',
        'logo_domain': 'easi-training.fr',
        'description': 'Plateforme de formation',
        'verrouille': True,
        'domaines': [
            'easi-training.fr',
            'connect.easi-training.fr',
            'cdn.easi-training.fr',
            'backend.connect.easi-training.fr',
            'backend.easi-training.fr',
            'notifications.easi-training.fr',
            'fonts.gstatic.com',
        ]
    },
    'netypareo': {
        'nom': 'NetYParéo',
        'icone': 'NP',
        'logo_domain': 'netypareo-formation-industries-auvergne.fr',
        'description': 'Gestion de la formation',
        'verrouille': True,
        'domaines': [
            'netypareo-formation-industries-auvergne.fr',
        ]
    },
    # --- Autres packs ---
    'youtube': {
        'nom': 'YouTube',
        'icone': '▶',
        'logo_domain': 'youtube.com',
        'description': 'Vidéos éducatives',
        'domaines': [
            'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be',
            'googlevideo.com', 'ytimg.com', 'yt3.ggpht.com',
            'youtubei.googleapis.com', 'youtube-ui.l.google.com',
        ]
    },
    'google': {
        'nom': 'Google',
        'icone': 'G',
        'logo_domain': 'google.com',
        'description': 'Recherche, Docs, Drive, Gmail',
        'domaines': [
            'google.com', 'google.fr', 'www.google.com', 'www.google.fr',
            'googleapis.com', 'gstatic.com', 'ssl.gstatic.com',
            'googleusercontent.com', 'lh3.googleusercontent.com',
            'accounts.google.com', 'docs.google.com', 'drive.google.com',
            'sheets.google.com', 'slides.google.com',
            'mail.google.com', 'gmail.com', 'googlemail.com',
            'fonts.googleapis.com', 'fonts.gstatic.com',
            'play.google.com', 'clients1.google.com',
        ]
    },
    'office365': {
        'nom': 'Office 365',
        'icone': 'M',
        'logo_domain': 'microsoft.com',
        'description': 'Word, Excel, Teams, Outlook',
        'domaines': [
            'office.com', 'office365.com', 'microsoft.com',
            'microsoftonline.com', 'live.com', 'outlook.com',
            'sharepoint.com', 'onedrive.com', 'onenote.com',
            'skype.com', 'windows.net', 'microsoft365.com',
            'msftauth.net', 'msocdn.com', 'akamaized.net',
            'login.microsoftonline.com', 'login.windows.net',
            'login.live.com', 'teams.microsoft.com',
            'outlook.office.com', 'outlook.office365.com',
        ]
    },
    'kahoot': {
        'nom': 'Kahoot',
        'icone': 'K',
        'logo_domain': 'kahoot.com',
        'description': 'Quiz interactifs',
        'domaines': [
            'kahoot.com', 'kahoot.it',
        ]
    },
    'wordreference': {
        'nom': 'WordReference',
        'icone': 'Wr',
        'logo_domain': 'wordreference.com',
        'description': 'Dictionnaire en ligne',
        'domaines': [
            'wordreference.com', 'www.wordreference.com',
        ]
    },
    'canva': {
        'nom': 'Canva',
        'icone': 'Cv',
        'logo_domain': 'canva.com',
        'description': 'Création graphique',
        'domaines': [
            'canva.com', 'www.canva.com', 'canva-apps.com',
            'canvaassets.com', 'canva.dev',
        ]
    },
    'linguee': {
        'nom': 'Linguee',
        'icone': 'Li',
        'logo_domain': 'linguee.fr',
        'description': 'Traduction contextuelle',
        'domaines': [
            'linguee.fr', 'linguee.com', 'www.linguee.fr',
        ]
    },
    'mistral': {
        'nom': 'Mistral AI',
        'icone': 'AI',
        'logo_domain': 'mistral.ai',
        'description': 'Assistant IA',
        'domaines': [
            'mistral.ai', 'chat.mistral.ai',
        ]
    },
    'nathan': {
        'nom': 'Manuels Nathan',
        'icone': 'N',
        'logo_domain': 'nathan.fr',
        'description': 'Manuels scolaires i-Manuel',
        'domaines': [
            'nathan.fr', 'editions-nathan.com',
            'e-interforum.com', 'campus.i-manuel.fr',
        ]
    },
}

# Fichier JSON pour stocker l'état des packs (activé/désactivé)
PACKS_STATE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'packs_state.json')


def _load_packs_state():
    """Charge l'état des packs depuis le fichier JSON"""
    try:
        with open(PACKS_STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Par défaut, tous les packs sont désactivés
        return {pack_id: False for pack_id in SITE_PACKS}


def _save_packs_state(state):
    """Sauvegarde l'état des packs dans le fichier JSON"""
    os.makedirs(os.path.dirname(PACKS_STATE_FILE), exist_ok=True)
    with open(PACKS_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_packs_with_state():
    """Retourne les packs avec leur état actuel"""
    state = _load_packs_state()
    packs = []
    for pack_id, pack_info in SITE_PACKS.items():
        verrouille = pack_info.get('verrouille', False)
        packs.append({
            'id': pack_id,
            'nom': pack_info['nom'],
            'icone': pack_info['icone'],
            'logo_domain': pack_info['logo_domain'],
            'description': pack_info['description'],
            'domaines': pack_info['domaines'],
            'nb_domaines': len(pack_info['domaines']),
            'verrouille': verrouille,
            # Les packs verrouillés sont toujours actifs
            'actif': True if verrouille else state.get(pack_id, False),
        })
    return packs


def _get_all_active_domains():
    """Retourne la liste de tous les domaines des packs activés"""
    state = _load_packs_state()
    domains = []
    for pack_id, pack_info in SITE_PACKS.items():
        # Toujours inclure les packs verrouillés + les packs activés manuellement
        if pack_info.get('verrouille', False) or state.get(pack_id, False):
            domains.extend(pack_info['domaines'])
    return list(set(domains))  # Dédupliquer


class FirewallManager:
    """Gestionnaire des règles de pare-feu pour les modes de filtrage"""
    
    def __init__(self):
        self.api = opnsense
    
    def test_connexion(self):
        return self.api.test_connexion()
    
    def get_mode_actuel(self):
        return get_mode_actif()
    
    def changer_mode(self, nouveau_mode, formateur_id=None):
        modes_valides = ['total', 'partiel', 'aucun']
        if nouveau_mode not in modes_valides:
            return {'success': False, 'message': f'Mode invalide'}
        
        try:
            set_mode_actif(nouveau_mode, formateur_id)
            result = self._appliquer_mode(nouveau_mode)
            
            if result['success']:
                return {'success': True, 'message': f'Mode changé vers "{nouveau_mode}"'}
            else:
                return {'success': False, 'message': f'Erreur OPNsense: {result.get("error", "?")}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _appliquer_mode(self, mode):
        """Applique les règles correspondant au mode"""
        try:
            if mode == 'total':
                self.api.toggle_filter_rule(RULE_UUIDS['guillotine'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['dns_local'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_http'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_https'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['app_work'], enabled=False)
                
            elif mode == 'partiel':
                # Synchroniser la whitelist avec les packs activés
                self._sync_whitelist_from_packs()
                self.api.toggle_filter_rule(RULE_UUIDS['dns_local'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_http'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_https'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['app_work'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['guillotine'], enabled=True)
                
            elif mode == 'aucun':
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_http'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['whitelist_https'], enabled=False)
                self.api.toggle_filter_rule(RULE_UUIDS['dns_local'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['app_work'], enabled=True)
                self.api.toggle_filter_rule(RULE_UUIDS['guillotine'], enabled=True)
            
            return self.api.apply_filter_rules()
            
        except Exception as e:
            print(f"[ERREUR] Application du mode {mode}: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # Gestion des packs
    # =========================================================================
    
    def toggle_pack(self, pack_id, activer):
        """Active ou désactive un pack de sites"""
        if pack_id not in SITE_PACKS:
            return {'success': False, 'message': 'Pack inconnu'}
        
        # Vérifier les dépendances (Gmail nécessite Google)
        state = _load_packs_state()
        
        if pack_id == 'google' and not activer:
            # Si on désactive Google, vérifier qu'aucun pack dépendant n'est actif
            # (YouTube a besoin de googleapis aussi)
            pass  # On laisse l'utilisateur gérer
        
        state[pack_id] = activer
        _save_packs_state(state)
        
        # Si on est en mode partiel, synchroniser immédiatement
        mode_actuel = get_mode_actif()
        if mode_actuel == 'partiel':
            self._sync_whitelist_from_packs()
            self.api.apply_filter_rules()
        
        action = "activé" if activer else "désactivé"
        return {'success': True, 'message': f'{SITE_PACKS[pack_id]["nom"]} {action}'}
    
    def _sync_whitelist_from_packs(self):
        """Synchronise l'alias WHITELIST_PARTIEL avec les packs activés"""
        domains = _get_all_active_domains()
        
        if not domains:
            # Si aucun pack actif, mettre un domaine bidon pour pas que l'alias soit vide
            domains = ['localhost']
        
        content = '\n'.join(domains)
        result = self.api.update_alias(ALIAS_UUIDS['whitelist_partiel'], content)
        if result['success']:
            self.api.reconfigure_aliases()
        return result


# Instance singleton
firewall_manager = FirewallManager()
