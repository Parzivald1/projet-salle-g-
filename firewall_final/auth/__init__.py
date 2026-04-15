"""
Module Auth
Authentification et gestion des sessions formateurs
"""

from .formateur import (
    authentifier_formateur,
    changer_code_formateur,
    verifier_session_active,
    deconnecter_formateur,
    login_required
)
