"""
Configuration - Interface Formateur Salle G
Raspberry Pi - Administration du pare-feu uniquement
"""

import os

# =============================================================================
# CONFIGURATION RÉSEAU
# =============================================================================

# OPNsense - HTTP (pas de HTTPS sur ce pare-feu)
OPNSENSE_IP = "192.168.1.1"
OPNSENSE_API_URL = f"http://{OPNSENSE_IP}/api"
OPNSENSE_API_KEY = "9Dz9g+Gwohb3PqxMoi+Ryhy7FCQnT46gQLfZVny+Xf6Q2mA46NRnBUYRi2ChU1wdKyYmA2tGeTz/yox8"
OPNSENSE_API_SECRET = "y7v8OX0rgzWHZCxcSCXpdtoa223/7lRYwNVH6S7lJZ3hThdTQk5xRAakCoM5MZudeXQBmOY8FDjNoZ7f"
OPNSENSE_VERIFY_SSL = False
CAPTIVE_PORTAL_ZONE_ID = 0

# VLAN Salle G
VLAN_SALLE_G_NETWORK = "192.168.2.0/24"

# Raspberry Pi
RASPBERRY_PI_IP = "192.168.3.54"
PORTAIL_PORT = 80

# =============================================================================
# CONFIGURATION APPLICATION
# =============================================================================

SECRET_KEY = os.environ.get('SECRET_KEY', 'uimm-portail-captif-secret-key-2024-change-me')
DEBUG = False
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'portail.db')
SESSION_TIMEOUT_MINUTES = 15

# Configuration Zenarmor
# Configuration Admin / Monitoring
ADMIN_CODE = "999999"       # Code pour accéder au monitoring réseau
ZENARMOR_CODE = "888888"    # Code pour accéder à l'interface Zenarmor (ancien 999999)
# Utilisation de la racine locale (port 80) grâce à la magie de Nginx
ZENARMOR_URL = f"http://{RASPBERRY_PI_IP}/ui/zenarmor/" 

# =============================================================================
# MODES DE FILTRAGE
# =============================================================================

MODES = {
    'total': {
        'nom': 'Accès Total',
        'description': 'Accès complet sauf catégories bloquées',
        'icone': 'globe'
    },
    'partiel': {
        'nom': 'Accès Partiel',
        'description': 'Accès uniquement aux sites de la liste blanche',
        'icone': 'list'
    },
    'aucun': {
        'nom': 'Aucun Accès',
        'description': 'Pas d\'accès internet (sauf Office 365)',
        'icone': 'lock'
    }
}

MODE_DEFAUT = 'total'

CATEGORIES_BLOQUEES = [
    'adult', 'porn', 'gambling', 'social-networks',
    'gaming', 'streaming-media', 'proxy-anonymizer',
    'malware', 'phishing'
]

WHITELIST_DEFAUT = [
    'wikipedia.org', 'fr.wikipedia.org',
    'easitraining.com', 'youtube.com', 'www.youtube.com'
]

DOMAINES_OFFICE365 = [
    '*.office.com', '*.office365.com', '*.microsoft.com',
    '*.microsoftonline.com', '*.windows.net', '*.azure.com',
    '*.sharepoint.com', '*.onedrive.com', '*.onenote.com',
    '*.outlook.com', '*.live.com', '*.skype.com',
    '*.teams.microsoft.com', 'login.microsoftonline.com',
    'login.windows.net', 'login.live.com'
]

NOMBRE_FORMATEURS = 10
