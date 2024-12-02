from functools import wraps

import pyotp
from flask import Flask, url_for, redirect, flash

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
import secrets

import flask_login
from flask_login import LoginManager, UserMixin
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# CAPTCHA KEYS
app.config['RECAPTCHA_PUBLIC_KEY'] = "6LdgyVUqAAAAAOlpHkzRlx7dr2F0SYp3QTp5Mo96"
app.config['RECAPTCHA_PRIVATE_KEY'] = "6LdgyVUqAAAAANmq8UrWlHqa4taLr7ZR8nJWh_Pd"

# DATABASE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///csc2031blog.db'
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

    # User information
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)

    # User posts
    posts = db.relationship("Post", order_by=Post.id, back_populates="user")

    def __init__(self, email, firstname, lastname, phone, password):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.phone = phone
        self.password = password
        self.mfa_enabled = False
        self.mfa_key = pyotp.random_base32()

    def verify_password(self, _submitted):
        return _submitted == self.password

    def verify_pin(self, _submitted):
        return pyotp.TOTP(self.mfa_key).verify(_submitted)

    @property
    def uri(self):
        return str(pyotp.totp.TOTP(self.mfa_key).provisioning_uri(self.email, "2031 Blog"))

    @property
    def is_active(self):
        return self.active

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))


# DATABASE ADMINISTRATOR
class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('index')


class PostView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('id', 'userid', 'created', 'title', 'body', 'user')

    def is_accessible(self):
        return flask_login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        flash('Access Denied.', category='danger')
        return redirect(url_for('posts.posts'))


class UserView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('id', 'email', 'password', 'firstname', 'lastname', 'phone', 'posts', 'mfa_enabled', 'mfa_key')

    def is_accessible(self):
        return flask_login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        flash('Access Denied.', category='danger')
        return redirect(url_for('posts.posts'))


admin = Admin(app, name='DB Admin', template_mode='bootstrap4')
admin._menu = admin._menu[1:]
app.config['FLASK_ADMIN_FLUID_LAYOUT'] = True
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

# RATE LIMITING
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=["500/day"])

# IMPORT BLUEPRINTS
from accounts.views import accounts_bp
from posts.views import posts_bp
from security.views import security_bp

# SECRET KEY FOR FLASK FORMS
app.config['SECRET_KEY'] = secrets.token_hex(16)

# REGISTER BLUEPRINTS
app.register_blueprint(accounts_bp)
app.register_blueprint(posts_bp)
app.register_blueprint(security_bp)
