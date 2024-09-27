from flask import Flask

app = Flask(__name__)

# IMPORT BLUEPRINTS
from accounts.views import accounts_bp