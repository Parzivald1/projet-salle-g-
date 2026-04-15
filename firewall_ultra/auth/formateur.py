"""
Authentification des formateurs
Gestion des sessions et vérification des codes
"""

import secrets
import functools
from flask import request, redirect, url_for, session, flash
from database.models import (
    verifier_code,
    changer_code,
    mettre_a_jour_connexion,
    creer_session,
    verifier_session,
    supprimer_session,
    nettoyer_sessions_expirees
)
from config import SESSION_TIMEOUT_MINUTES


def generer_token():
    """Génère un token de session sécurisé"""
    return secrets.token_hex(32)


def authentifier_formateur(code):
    """
    Authentifie un formateur avec son code
    
    Args:
        code: Code à 6 chiffres du formateur
    
    Returns:
        dict avec 'success', 'formateur', 'premier_login', 'token'
    """
    # Nettoyer les sessions expirées
    nettoyer_sessions_expirees()
    
    # Vérifier le code
    formateur = verifier_code(code)
    
    if not formateur:
        return {
            'success': False,
            'message': 'Code invalide'
        }
    
    # Créer une session
    token = generer_token()
    creer_session(formateur['id'], token, SESSION_TIMEOUT_MINUTES)
    
    # Mettre à jour la dernière connexion
    mettre_a_jour_connexion(formateur['id'])
    
    return {
        'success': True,
        'formateur': formateur,
        'premier_login': formateur['premier_login'],
        'token': token
    }


def changer_code_formateur(formateur_id, ancien_code, nouveau_code, confirmation_code):
    """
    Change le code d'un formateur
    
    Args:
        formateur_id: ID du formateur
        ancien_code: Code actuel (pour vérification)
        nouveau_code: Nouveau code souhaité
        confirmation_code: Confirmation du nouveau code
    
    Returns:
        dict avec 'success' et 'message'
    """
    # Vérifications
    if nouveau_code != confirmation_code:
        return {
            'success': False,
            'message': 'Les deux codes ne correspondent pas'
        }
    
    if len(nouveau_code) != 6 or not nouveau_code.isdigit():
        return {
            'success': False,
            'message': 'Le code doit contenir exactement 6 chiffres'
        }
    
    if nouveau_code == ancien_code:
        return {
            'success': False,
            'message': 'Le nouveau code doit être différent de l\'ancien'
        }
    
    # Vérifier l'ancien code
    formateur = verifier_code(ancien_code)
    if not formateur or formateur['id'] != formateur_id:
        return {
            'success': False,
            'message': 'Code actuel incorrect'
        }
    
    # Changer le code
    if changer_code(formateur_id, nouveau_code):
        return {
            'success': True,
            'message': 'Code changé avec succès'
        }
    else:
        return {
            'success': False,
            'message': 'Ce code est déjà utilisé par un autre formateur'
        }


def verifier_session_active(token):
    """
    Vérifie si une session est active et valide
    
    Args:
        token: Token de session
    
    Returns:
        dict avec infos du formateur si valide, None sinon
    """
    if not token:
        return None
    
    return verifier_session(token)


def deconnecter_formateur(token):
    """
    Déconnecte un formateur en supprimant sa session
    
    Args:
        token: Token de session à supprimer
    """
    if token:
        supprimer_session(token)


def login_required(f):
    """
    Décorateur pour protéger les routes nécessitant une authentification
    
    Usage:
        @app.route('/admin')
        @login_required
        def admin():
            ...
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        
        if not token:
            flash('Veuillez vous connecter', 'error')
            return redirect(url_for('portail'))
        
        formateur = verifier_session_active(token)
        
        if not formateur:
            session.clear()
            flash('Session expirée, veuillez vous reconnecter', 'error')
            return redirect(url_for('portail'))
        
        # Ajouter les infos du formateur au contexte
        request.formateur = formateur
        
        return f(*args, **kwargs)
    
    return decorated_function
