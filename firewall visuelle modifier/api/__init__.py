"""
Module API
Communication avec OPNsense et gestion des règles firewall
"""

from .opnsense import opnsense, OPNsenseAPI
from .firewall_rules import firewall_manager, FirewallManager
