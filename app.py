from config import app
from flask import render_template

@app.route('/')
def index():
    return render_template('home/index.html')

@app.errorhandler(429)
def http429(e):
    return render_template('errors/429.html')

if __name__ == '__main__':
    app.run()