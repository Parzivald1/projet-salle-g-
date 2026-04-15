"""
Communication avec l'API OPNsense
Gestion des règles de pare-feu uniquement (pas de captive portal)
"""

import requests
import urllib3
from config import (
    OPNSENSE_API_URL,
    OPNSENSE_API_KEY,
    OPNSENSE_API_SECRET,
    OPNSENSE_VERIFY_SSL,
    DOMAINES_OFFICE365
)

if not OPNSENSE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OPNsenseAPI:
    def __init__(self):
        self.base_url = OPNSENSE_API_URL
        self.auth = (OPNSENSE_API_KEY, OPNSENSE_API_SECRET)
        self.verify_ssl = OPNSENSE_VERIFY_SSL
        self.timeout = 10
    
    def _request(self, method, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == 'GET':
                response = requests.get(url, auth=self.auth, verify=self.verify_ssl, timeout=self.timeout)
            elif method == 'POST':
                response = requests.post(url, auth=self.auth, json=data if data else {}, verify=self.verify_ssl, timeout=self.timeout)
            else:
                raise ValueError(f"Méthode non supportée: {method}")
            response.raise_for_status()
            try:
                return {'success': True, 'data': response.json()}
            except ValueError:
                return {'success': True, 'data': {'status': 'ok'}}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Impossible de se connecter à OPNsense'}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Timeout'}
        except requests.exceptions.HTTPError as e:
            return {'success': False, 'error': f'Erreur HTTP {e.response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_connexion(self):
        result = self._request('GET', 'core/firmware/status')
        return result['success']
    
    # Alias
    def get_aliases(self):
        return self._request('GET', 'firewall/alias/searchItem')
    
    def update_alias(self, uuid, content):
        return self._request('POST', f'firewall/alias/setItem/{uuid}', {'alias': {'content': content}})
    
    def reconfigure_aliases(self):
        return self._request('POST', 'firewall/alias/reconfigure')
    
    # Règles firewall
    def get_filter_rules(self):
        return self._request('GET', 'firewall/filter/searchRule')
    
    def toggle_filter_rule(self, uuid, enabled=True):
        return self._request('POST', f'firewall/filter/setRule/{uuid}', {'rule': {'enabled': '1' if enabled else '0'}})
    
    def apply_filter_rules(self):
        return self._request('POST', 'firewall/filter/apply')


opnsense = OPNsenseAPI()
