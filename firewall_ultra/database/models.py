"""
Modèles de base de données SQLite
"""

import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_db_connection():
    """Crée une connexion à la base de données SQLite"""
    # Créer le dossier data s'il n'existe pas
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn


def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table des formateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(6) NOT NULL UNIQUE,
            premier_login BOOLEAN DEFAULT 1,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            derniere_connexion TIMESTAMP
        )
    ''')
    
    # Table du mode actif (une seule ligne)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mode_actif (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            mode VARCHAR(20) NOT NULL DEFAULT 'total',
            modifie_par INTEGER,
            date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (modifie_par) REFERENCES formateurs(id)
        )
    ''')
    
    # Table whitelist pour le mode "Accès Partiel"
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist_partiel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domaine VARCHAR(255) NOT NULL UNIQUE,
            ajoute_par INTEGER,
            date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ajoute_par) REFERENCES formateurs(id)
        )
    ''')
    
    # Table blacklist pour le mode "Accès Total" (sites supplémentaires à bloquer)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist_total (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domaine VARCHAR(255) NOT NULL UNIQUE,
            ajoute_par INTEGER,
            date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ajoute_par) REFERENCES formateurs(id)
        )
    ''')
    
    # Table des sessions actives
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formateur_id INTEGER NOT NULL,
            token VARCHAR(64) NOT NULL UNIQUE,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_expiration TIMESTAMP NOT NULL,
            FOREIGN KEY (formateur_id) REFERENCES formateurs(id)
        )
    ''')
    
    conn.commit()
    conn.close()


# =============================================================================
# FONCTIONS FORMATEURS
# =============================================================================

def creer_formateur(code):
    """Crée un nouveau formateur avec un code initial"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO formateurs (code, premier_login) VALUES (?, 1)',
            (code,)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Code déjà existant
    finally:
        conn.close()


def verifier_code(code):
    """Vérifie si un code formateur existe et retourne ses infos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, code, premier_login FROM formateurs WHERE code = ?',
        (code,)
    )
    formateur = cursor.fetchone()
    conn.close()
    return dict(formateur) if formateur else None


def changer_code(formateur_id, nouveau_code):
    """Change le code d'un formateur et marque premier_login à False"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''UPDATE formateurs 
               SET code = ?, premier_login = 0, derniere_connexion = ? 
               WHERE id = ?''',
            (nouveau_code, datetime.now(), formateur_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False  # Code déjà utilisé par un autre formateur
    finally:
        conn.close()


def mettre_a_jour_connexion(formateur_id):
    """Met à jour la date de dernière connexion"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE formateurs SET derniere_connexion = ? WHERE id = ?',
        (datetime.now(), formateur_id)
    )
    conn.commit()
    conn.close()


# =============================================================================
# FONCTIONS MODE
# =============================================================================

def get_mode_actif():
    """Récupère le mode de filtrage actif"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT mode FROM mode_actif WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['mode']
    else:
        # Initialiser avec le mode par défaut
        set_mode_actif('total', None)
        return 'total'


def set_mode_actif(mode, formateur_id):
    """Change le mode de filtrage actif"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Upsert (insert or update)
    cursor.execute('''
        INSERT INTO mode_actif (id, mode, modifie_par, date_modification)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            mode = excluded.mode,
            modifie_par = excluded.modifie_par,
            date_modification = excluded.date_modification
    ''', (mode, formateur_id, datetime.now()))
    
    conn.commit()
    conn.close()
    return True


# =============================================================================
# FONCTIONS WHITELIST / BLACKLIST
# =============================================================================

def get_whitelist_partiel():
    """Récupère la liste blanche du mode partiel"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, domaine, date_ajout FROM whitelist_partiel ORDER BY date_ajout DESC')
    sites = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sites


def ajouter_whitelist_partiel(domaine, formateur_id):
    """Ajoute un domaine à la whitelist du mode partiel"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO whitelist_partiel (domaine, ajoute_par) VALUES (?, ?)',
            (domaine.lower().strip(), formateur_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Domaine déjà présent
    finally:
        conn.close()


def supprimer_whitelist_partiel(domaine_id):
    """Supprime un domaine de la whitelist du mode partiel"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM whitelist_partiel WHERE id = ?', (domaine_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def get_blacklist_total():
    """Récupère la liste noire du mode total"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, domaine, date_ajout FROM blacklist_total ORDER BY date_ajout DESC')
    sites = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sites


def ajouter_blacklist_total(domaine, formateur_id):
    """Ajoute un domaine à la blacklist du mode total"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO blacklist_total (domaine, ajoute_par) VALUES (?, ?)',
            (domaine.lower().strip(), formateur_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Domaine déjà présent
    finally:
        conn.close()


def supprimer_blacklist_total(domaine_id):
    """Supprime un domaine de la blacklist du mode total"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM blacklist_total WHERE id = ?', (domaine_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


# =============================================================================
# FONCTIONS SESSIONS
# =============================================================================

def creer_session(formateur_id, token, duree_minutes=15):
    """Crée une nouvelle session pour un formateur"""
    from datetime import timedelta
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    date_expiration = datetime.now() + timedelta(minutes=duree_minutes)
    
    cursor.execute(
        'INSERT INTO sessions (formateur_id, token, date_expiration) VALUES (?, ?, ?)',
        (formateur_id, token, date_expiration)
    )
    conn.commit()
    conn.close()
    return True


def verifier_session(token):
    """Vérifie si une session est valide et non expirée"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.formateur_id, f.code 
        FROM sessions s
        JOIN formateurs f ON s.formateur_id = f.id
        WHERE s.token = ? AND s.date_expiration > ?
    ''', (token, datetime.now()))
    session = cursor.fetchone()
    conn.close()
    return dict(session) if session else None


def supprimer_session(token):
    """Supprime une session (déconnexion)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()


def nettoyer_sessions_expirees():
    """Supprime toutes les sessions expirées"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE date_expiration < ?', (datetime.now(),))
    conn.commit()
    conn.close()
