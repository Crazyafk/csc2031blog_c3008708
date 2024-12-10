import re

import flask

from config import app
from flask import render_template


@app.route('/')
def index():
    return render_template('home/index.html')


@app.before_request
def firewall():
    conditions = {
        "SQL Injection": re.compile(r"union|select|insert|drop|alter|;|`|'", re.IGNORECASE),
        "XXS": re.compile(r"<script>|<iframe>|%3Cscript%3C|%3Ciframe%3C", re.IGNORECASE),
        "Path Traversal": re.compile(r"\.\./|\.\.|%2e%2e%2f|%2e%2e/|\.\.%2f", re.IGNORECASE)
    }
    for attack_type, attack_pattern in conditions.items():
        if attack_pattern.search(flask.request.path) or attack_pattern.search(flask.request.query_string.decode()):
            return render_template('errors/attack.html', attack_type=attack_type)


@app.errorhandler(400)
def http400(e):
    return render_template('errors/400.html')


@app.errorhandler(404)
def http404(e):
    return render_template('errors/404.html')


@app.errorhandler(429)
def http429(e):
    return render_template('errors/429.html')


@app.errorhandler(500)
def http500(e):
    return render_template('errors/500.html')


@app.errorhandler(501)
def http501(e):
    return render_template('errors/501.html')


if __name__ == '__main__':
    app.run()