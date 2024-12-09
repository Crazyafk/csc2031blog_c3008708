from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import asc
import os

from config import roles_required, Log, logger

security_bp = Blueprint('security', __name__, template_folder='templates')

@security_bp.route('/security')
@login_required
@roles_required("/security", "sec_admin")
def security():
    all_logs = Log.query.order_by(asc('id')).all()
    log_file = open('security.log', 'r')
    recent_log_file = tail(log_file, 10)
    recent_log_file.reverse()
    log_file.close()
    return render_template('security/security.html', logs=all_logs, logfile=recent_log_file)


# with thanks to glenbot on stackoverflow (https://stackoverflow.com/a/13790289)
def tail(f, lines=1, _buffer=4098):
    """Tail a file and get X lines from the end"""
    # place holder for the lines found
    lines_found = []

    # block counter will be multiplied by buffer
    # to get the block size from the end
    block_counter = -1

    # loop until we find X lines
    while len(lines_found) < lines:
        try:
            f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # either file is too small, or too many lines requested
            f.seek(0)
            lines_found = f.readlines()
            break

        lines_found = f.readlines()

        # we found enough lines, get out
        # Removed this line because it was redundant the while will catch
        # it, I left it for history
        # if len(lines_found) > lines:
        #    break

        # decrement the block counter to get the
        # next X bytes
        block_counter -= 1

    return lines_found[-lines:]