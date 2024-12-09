from config import app
from flask import render_template


@app.route('/')
def index():
    return render_template('home/index.html')


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