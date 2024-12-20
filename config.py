import base64
import logging
import os
from functools import wraps
from dotenv import load_dotenv, set_key

import flask
import pyotp
from cryptography.fernet import Fernet
from flask import Flask, url_for, redirect, flash, render_template

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
import secrets

import flask_login
from flask_login import LoginManager, UserMixin
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_talisman import Talisman
from sqlalchemy import MetaData
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from argon2 import PasswordHasher
from hashlib import scrypt

load_dotenv()
app = Flask(__name__)

# CAPTCHA KEYS
app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv('RECAPTCHA_PUBLIC_KEY')
app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv('RECAPTCHA_PRIVATE_KEY')

# DATABASE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_ECHO'] = (os.getenv('SQLALCHEMY_ECHO') == "True")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = (os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS') == "True")

metadata = MetaData(
    naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app, db)

# CREATE LOGIN MANAGER
login_manager = LoginManager()
login_manager.login_view = 'accounts.login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)

# INIT QRCODE
qrcode = QRcode(app)

# INIT LOGGER
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Security Log")
handler = logging.FileHandler('security.log')
handler.setLevel(0)
formatter = logging.Formatter('%(asctime)s : %(message)s', '%d/%m/%Y %I:%M:%S %p')
handler.setFormatter(formatter)
logger.addHandler(handler)

# INIT HASHING
ph = PasswordHasher()


# DATABASE TABLES
class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    created = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    user = db.relationship("User", back_populates="posts")

    def __init__(self, userid, title, body):
        self.created = datetime.now()
        self.title = title
        self.body = body
        self.userid = userid

    def update(self, title, body):
        self.created = datetime.now()
        self.title = title
        self.body = body
        db.session.commit()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # User authentication information.
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    mfa_enabled = db.Column(db.Boolean, nullable=False)
    mfa_key = db.Column(db.String(32), nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)

    # User role. Possible values: 'end_user', 'sec_admin', 'db_admin'
    role = db.Column(db.String(20), default='end_user', nullable=False)

    # Other
    salt = db.Column(db.String(100), nullable=False)

    # User information
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)

    # Relationships
    posts = db.relationship("Post", order_by=Post.id, back_populates="user")
    log = db.relationship("Log", uselist=False, back_populates="user")

    def __init__(self, email, firstname, lastname, phone, password):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.phone = phone
        self.password = password
        self.mfa_enabled = False
        self.mfa_key = pyotp.random_base32()
        self.salt = base64.b64encode(secrets.token_bytes(32)).decode()

    def generate_log(self):
        db.session.add(Log(self.id))
        db.session.commit()

    def verify_password(self, _submitted):
        return ph.verify(self.password, _submitted)

    def verify_pin(self, _submitted):
        return pyotp.TOTP(self.mfa_key).verify(_submitted)

    @property
    def uri(self):
        return str(pyotp.totp.TOTP(self.mfa_key).provisioning_uri(self.email, "2031 Blog"))

    @property
    def key(self):
        return base64.b64encode(scrypt(password=self.password.encode(), salt=self.salt.encode(),
                                       n=2048, r=8, p=1, dklen=32))

    @property
    def fernet(self):
        return Fernet(self.key)

    def encrypt(self, data):
        return self.fernet.encrypt(data.encode())

    def decrypt(self, data):
        return self.fernet.decrypt(data).decode()

    @property
    def is_active(self):
        return self.active

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))


class Log(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", back_populates="log")

    registration = db.Column(db.DateTime, nullable=False)
    latest_login = db.Column(db.DateTime)
    previous_login = db.Column(db.DateTime)
    latest_login_ip = db.Column(db.String)
    previous_login_ip = db.Column(db.String)

    def __init__(self, user_id):
        self.user_id = user_id
        self.registration = datetime.now()

    def login(self):
        self.previous_login = self.latest_login
        self.previous_login_ip = self.latest_login_ip
        self.latest_login = datetime.now()
        self.latest_login_ip = flask.request.remote_addr
        db.session.commit()


# DATABASE ADMINISTRATOR
class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('index')


class PostView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('id', 'userid', 'created', 'title', 'body', 'user')

    can_edit = False
    can_create = False
    can_delete = False

    def is_accessible(self):
        return flask_login.current_user.is_authenticated and flask_login.current_user.role == "db_admin"

    def inaccessible_callback(self, name, **kwargs):
        if flask_login.current_user.is_authenticated:
            user = flask_login.current_user
            logger.info(f"Unauthorised Role Access Attempt. Email: {user.email} Role: {user.role}"
                        f" Requested URL: /admin/ IP:{flask.request.remote_addr}")
            return render_template('errors/403.html')
        else:
            flash("Login to view this Page.", category='info')
            return redirect(url_for('accounts.login'))


class UserView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = (
        'id', 'role', 'email', 'password', 'firstname', 'lastname', 'phone', 'posts', 'mfa_enabled', 'mfa_key', 'salt')

    can_edit = False
    can_create = False
    can_delete = False

    def is_accessible(self):
        return flask_login.current_user.is_authenticated and flask_login.current_user.role == "db_admin"

    def inaccessible_callback(self, name, **kwargs):
        if flask_login.current_user.is_authenticated:
            user = flask_login.current_user
            logger.info(f"Unauthorised Role Access Attempt. Email: {user.email} Role: {user.role}"
                        f" Requested URL: /admin/ IP:{flask.request.remote_addr}")
            return render_template('errors/403.html')
        else:
            flash("Login to view this Page.", category='info')
            return redirect(url_for('accounts.login'))


admin = Admin(app, name='DB Admin', template_mode='bootstrap4')
admin._menu = admin._menu[1:]
app.config['FLASK_ADMIN_FLUID_LAYOUT'] = (os.getenv('FLASK_ADMIN_FLUID_LAYOUT') == "True")
admin.add_link(MainIndexLink(name='Home Page'))
admin.add_view(PostView(Post, db.session))
admin.add_view(UserView(User, db.session))


# CUSTOM DECORATORS
def anonymous_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if flask_login.current_user.is_authenticated:
            flash('You are already logged in', category='success')
            return redirect(url_for('posts.posts'))
        return f(*args, **kwargs)

    return wrapped


def roles_required(url, *roles):
    def inner_decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if flask_login.current_user.role not in roles:
                user = flask_login.current_user
                logger.info(f"Unauthorised Role Access Attempt. Email: {user.email} Role: {user.role}"
                            f" Requested URL: {url} IP:{flask.request.remote_addr}")
                return render_template('errors/403.html')
            return f(*args, **kwargs)

        return wrapped

    return inner_decorator


# RATE LIMITING
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=["500/day"])

# IMPORT BLUEPRINTS
from accounts.views import accounts_bp
from posts.views import posts_bp
from security.views import security_bp

# SECRET KEY FOR FLASK FORMS
if os.getenv('SECRET_KEY'):
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
else:
    secret_key = secrets.token_hex(16)
    app.config['SECRET_KEY'] = secret_key
    set_key(".env", key_to_set='SECRET_KEY', value_to_set=secret_key)

# REGISTER BLUEPRINTS
app.register_blueprint(accounts_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(security_bp)

# SETUP TALISMAN
csp = {
    'xyz-src': ['\'self\''],
    'style-src': ["https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css",
                  "http://127.0.0.1:5000/admin/static/bootstrap/bootstrap4/swatch/default/bootstrap.min.css?v=4.2.1",
                "http://127.0.0.1:5000/admin/static/bootstrap/bootstrap4/css/bootstrap.min.css?v=4.2.1",
                  "http://127.0.0.1:5000/admin/static/admin/css/bootstrap4/admin.css?v=1.1.1",
                  "http://127.0.0.1:5000/admin/static/bootstrap/bootstrap4/css/font-awesome.min.css?v=4.7.0",
                  "http://127.0.0.1:5000/admin/static/vendor/select2/select2.css?v=4.2.1",
                  "http://127.0.0.1:5000/admin/static/vendor/select2/select2-bootstrap4.css?v=1.4.6",
                  "http://127.0.0.1:5000/admin/static/vendor/bootstrap-daterangepicker/daterangepicker-bs4.css?v=1.3.22"],
    'script-src': ["https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js",
                   "https://www.google.com/recaptcha/",
                   "https://www.gstatic.com/recaptcha/"],
    'frame-src': ["https://www.google.com/recaptcha/",
                  "https://www.gstatic.com/recaptcha/"]
}
talisman = Talisman(app, content_security_policy=csp)
