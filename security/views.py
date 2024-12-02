from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import asc

from config import roles_required, Log

security_bp = Blueprint('security', __name__, template_folder='templates')

@security_bp.route('/security')
@login_required
@roles_required("sec_admin")
def security():
    all_logs = Log.query.order_by(asc('id')).all()
    return render_template('security/security.html', logs=all_logs)