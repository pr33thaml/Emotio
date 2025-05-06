from flask import Blueprint, jsonify
from flask_login import login_required

bp = Blueprint('professionals', __name__)

@bp.route('/list')
@login_required
def get_professionals():
    # This would typically come from a database
    professionals = [
        {
            'name': 'Dr. Jane Smith',
            'specialty': 'Clinical Psychologist',
            'contact': 'contact@example.com'
        }
    ]
    return jsonify(professionals) 