from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from app.models.professional import Professional

bp = Blueprint('professionals', __name__)

@bp.route('/professionals')
@login_required
def list_professionals():
    professionals = Professional.get_all()
    return render_template('professionals.html', professionals=professionals)

@bp.route('/professionals/<professional_id>')
@login_required
def view_professional(professional_id):
    professional = Professional.get_by_id(professional_id)
    if professional:
        return render_template('professional_detail.html', professional=professional)
    return redirect(url_for('professionals.list_professionals')) 