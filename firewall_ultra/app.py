"""
Interface Formateur - Salle G
UIMM Pôle Formation Champagne-Ardenne

Raspberry Pi : gestion des modes de filtrage uniquement.
La connexion des élèves est gérée par le portail captif OPNsense.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import logging

from config import SECRET_KEY, DEBUG, MODES, SESSION_TIMEOUT_MINUTES, ZENARMOR_CODE, ZENARMOR_URL, ADMIN_CODE
from database.models import (
    init_db, get_mode_actif, get_whitelist_partiel, get_blacklist_total
)
from auth.formateur import (
    authentifier_formateur, changer_code_formateur,
    verifier_session_active, deconnecter_formateur, login_required
)
from api.firewall_rules import firewall_manager, get_packs_with_state
from api.dns_monitor import dns_buffer, start_dns_monitor

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# App
app = Flask(__name__)

from flask import session

app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

init_db()
start_dns_monitor()
logger.info("Interface formateur démarrée")


@app.template_filter('format_date')
def format_date(value):
    if value:
        from datetime import datetime
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime('%d/%m/%Y %H:%M')
    return ''


# =============================================================================
# PAGE D'ACCUEIL : Connexion formateur
# =============================================================================

@app.route('/')
def portail():
    """Page de connexion formateur"""
    mode_actif = get_mode_actif()
    return render_template('portail.html', mode_actif=mode_actif, modes=MODES)


@app.route('/connexion-formateur', methods=['POST'])
def connexion_formateur():
    """Connexion d'un formateur avec son code"""
    code = ''
    for i in range(1, 7):
        code += request.form.get(f'code{i}', '')
    
    if code == ADMIN_CODE:
        logger.info("Accès admin monitoring demandé via le portail")
        session['is_admin'] = True
        return redirect(url_for('admin_logs'))

    if code == ZENARMOR_CODE:
        logger.info("Accès Zenarmor demandé via le portail")
        return redirect(url_for('zenarmor_dashboard'))

    if len(code) != 6:
        flash('Code invalide', 'error')
        return redirect(url_for('portail'))
    
    result = authentifier_formateur(code)
    if not result['success']:
        flash(result['message'], 'error')
        return redirect(url_for('portail'))
    
    session['token'] = result['token']
    session['formateur_id'] = result['formateur']['id']
    
    if result['premier_login']:
        session['ancien_code'] = code
        return redirect(url_for('change_code'))
    
    return redirect(url_for('dashboard'))


# =============================================================================
# CHANGEMENT DE CODE
# =============================================================================

@app.route('/change-code')
def change_code():
    if 'formateur_id' not in session:
        return redirect(url_for('portail'))
    return render_template('change_code.html')


@app.route('/change-code', methods=['POST'])
def change_code_post():
    if 'formateur_id' not in session:
        return redirect(url_for('portail'))
    
    nouveau_code = ''
    confirmation_code = ''
    for i in range(1, 7):
        nouveau_code += request.form.get(f'nouveau{i}', '')
        confirmation_code += request.form.get(f'confirmation{i}', '')
    
    ancien_code = session.get('ancien_code', '')
    result = changer_code_formateur(session['formateur_id'], ancien_code, nouveau_code, confirmation_code)
    
    if result['success']:
        session.pop('ancien_code', None)
        flash('Code changé avec succès !', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash(result['message'], 'error')
        return redirect(url_for('change_code'))


# =============================================================================
# ADMINISTRATION
# =============================================================================

@app.route('/admin')
@login_required
def dashboard():
    mode_actif = get_mode_actif()
    packs = get_packs_with_state()
    return render_template('dashboard.html', mode_actif=mode_actif, modes=MODES, formateur=request.formateur, packs=packs)


@app.route('/admin/changer-mode', methods=['POST'])
@login_required
def changer_mode():
    if request.is_json:
        nouveau_mode = request.json.get('mode')
    else:
        nouveau_mode = request.form.get('mode')

    result = firewall_manager.changer_mode(nouveau_mode, request.formateur['formateur_id'])

    if request.is_json:
        if result['success']:
            return jsonify({'success': True, 'message': f'Mode {nouveau_mode} actif', 'mode': nouveau_mode})
        else:
            return jsonify({'success': False, 'message': result['message']}), 400

    if result['success']:
        flash(f'Mode changé : {MODES[nouveau_mode]["nom"]}', 'success')
    else:
        flash(result['message'], 'error')
    return redirect(url_for('dashboard'))


@app.route('/admin/toggle-pack', methods=['POST'])
@login_required
def toggle_pack():
    """Active ou désactive un pack de sites"""
    if request.is_json:
        pack_id = request.json.get('pack_id')
        activer = request.json.get('activer', True)
    else:
        pack_id = request.form.get('pack_id')
        activer = request.form.get('activer') == '1'

    result = firewall_manager.toggle_pack(pack_id, activer)

    if request.is_json:
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 400

    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    return redirect(url_for('dashboard'))


@app.route('/admin/update-packs', methods=['POST'])
@login_required
def update_packs():
    """Met à jour tous les packs d'un coup (batch)"""
    from api.firewall_rules import SITE_PACKS, _load_packs_state, _save_packs_state
    
    # Récupérer les packs cochés dans le formulaire
    active_packs = request.form.getlist('packs')

    # Construire le nouvel état : coché = True, pas coché = False
    # Les packs verrouillés sont toujours forcés à True
    new_state = {}
    for pack_id, pack_info in SITE_PACKS.items():
        if pack_info.get('verrouille', False):
            new_state[pack_id] = True
        else:
            new_state[pack_id] = (pack_id in active_packs)
    
    _save_packs_state(new_state)
    
    # Synchroniser avec le pare-feu si en mode partiel
    from database.models import get_mode_actif
    if get_mode_actif() == 'partiel':
        firewall_manager._sync_whitelist_from_packs()
        firewall_manager.api.apply_filter_rules()
    
    flash('Sites mis à jour avec succès', 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/gestion/<mode_type>')
@login_required
def gestion_acces(mode_type):
    if mode_type not in ['total', 'partiel']:
        flash('Type de gestion invalide', 'error')
        return redirect(url_for('dashboard'))
    
    if mode_type == 'partiel':
        sites = get_whitelist_partiel()
        titre = "Gestion de la liste blanche"
        description = "Sites autorisés en mode Accès Partiel"
    else:
        sites = get_blacklist_total()
        titre = "Gestion de la liste noire"
        description = "Sites bloqués en mode Accès Total"
    
    return render_template('gestion_acces.html', mode_type=mode_type, sites=sites,
                         titre=titre, description=description, formateur=request.formateur)


@app.route('/admin/ajouter-site', methods=['POST'])
@login_required
def ajouter_site():
    mode_type = request.form.get('mode_type')
    domaine = request.form.get('domaine', '').strip().lower()
    
    if not domaine:
        flash('Veuillez entrer un domaine', 'error')
        return redirect(url_for('gestion_acces', mode_type=mode_type))
    
    domaine = domaine.replace('http://', '').replace('https://', '')
    if domaine.startswith('www.'):
        domaine = domaine[4:]
    domaine = domaine.rstrip('/')
    
    if mode_type == 'partiel':
        result = firewall_manager.ajouter_site_whitelist(domaine, request.formateur['formateur_id'])
    else:
        result = firewall_manager.ajouter_site_blacklist(domaine, request.formateur['formateur_id'])
    
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('gestion_acces', mode_type=mode_type))


@app.route('/admin/supprimer-site', methods=['POST'])
@login_required
def supprimer_site():
    mode_type = request.form.get('mode_type')
    site_id = request.form.get('site_id')
    
    if mode_type == 'partiel':
        result = firewall_manager.supprimer_site_whitelist(site_id)
    else:
        result = firewall_manager.supprimer_site_blacklist(site_id)
    
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('gestion_acces', mode_type=mode_type))


# =============================================================================
# API
# =============================================================================

@app.route('/api/mode-actif')
def api_mode_actif():
    mode = get_mode_actif()
    return jsonify({'mode': mode, 'nom': MODES[mode]['nom'], 'description': MODES[mode]['description']})


@app.route('/api/test-opnsense')
@login_required
def api_test_opnsense():
    connected = firewall_manager.test_connexion()
    return jsonify({'connected': connected})


# =============================================================================
# ADMIN MONITORING (code 999999)
# =============================================================================

@app.route('/admin/monitoring')
def admin_logs():
    """Page de monitoring DNS - accès via code admin"""
    if not session.get('is_admin'):
        flash('Accès non autorisé', 'error')
        return redirect(url_for('portail'))
    return render_template('admin_logs.html')


@app.route('/api/admin/logs')
def api_admin_logs():
    """API : retourne les logs DNS agrégés"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    return jsonify(dns_buffer.get_snapshot())


@app.route('/api/admin/clear', methods=['POST'])
def api_admin_clear():
    """API : vide le buffer de logs"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Non autorisé'}), 403
    dns_buffer.clear()
    return jsonify({'success': True})


# =============================================================================
# ZENARMOR DASHBOARD
# =============================================================================

@app.route('/zenarmor')
def zenarmor_dashboard():
    """Page spéciale pour visualiser le trafic Zenarmor"""
    return render_template('zenarmor.html', zenarmor_url=ZENARMOR_URL)


# =============================================================================
# DÉCONNEXION
# =============================================================================

@app.route('/logout')
def logout():
    token = session.get('token')
    if token:
        deconnecter_formateur(token)
    session.clear()
    flash('Déconnexion réussie', 'success')
    return redirect(url_for('portail'))


@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('portail'))


@app.errorhandler(500)
def internal_error(e):
    return redirect(url_for('portail'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
