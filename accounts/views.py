import flask_login
from flask import Blueprint, render_template, flash, redirect, url_for, session
from accounts.forms import RegistrationForm, LoginForm
from config import User, db, limiter
from markupsafe import Markup

accounts_bp = Blueprint('accounts', __name__, template_folder='templates')


@accounts_bp.route('/registration', methods=['GET', 'POST'])
def registration():
    form = RegistrationForm()

    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', category="danger")
            return render_template('accounts/registration.html', form=form)

        new_user = User(email=form.email.data,
                        firstname=form.firstname.data,
                        lastname=form.lastname.data,
                        phone=form.phone.data,
                        password=form.password.data,
                        )

        db.session.add(new_user)
        db.session.commit()

        flash('Account Created. You must Set up MFA before logging in', category='success')
        return render_template('accounts/mfa.html', key=new_user.mfa_key, uri=new_user.uri)

    return render_template('accounts/registration.html', form=form)


@accounts_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20/minute')
def login():
    form = LoginForm()

    max_login_attempts = 3

    if not session.get("login attempts"):
        session["login attempts"] = 0

    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()

        # ----VALID LOGIN----
        if user and user.verify_password(form.password.data) and user.mfa_enabled and user.verify_pin(form.pin.data):
            flask_login.login_user(user)
            flash('Authentication Success', category='success')
            return redirect(url_for('posts.posts'))

        # ----MFA SETUP----
        elif user and user.verify_password(form.password.data) and not user.mfa_enabled:
            # ----VALID LOGIN ENABLING MFA----
            if user.verify_pin(form.pin.data):
                user.mfa_enabled = True
                db.session.commit()

                flask_login.login_user(user)
                flash('Authentication Success', category='success')
                return redirect(url_for('posts.posts'))

            # ----MUST SETUP MFA----
            else:
                flash('You must Set up MFA before logging in', category='success')
                return render_template('accounts/mfa.html', key=user.mfa_key, uri=user.uri)

        # ----INVALID--------
        else:
            session["login attempts"] += 1

            # ATTEMPTS REMAINING
            if session["login attempts"] < max_login_attempts:
                flash('Incorrect Credentials. {} Attempts Remaining'.format(
                    max_login_attempts - session["login attempts"]),
                    category='danger')
                return render_template('accounts/login.html', form=form)
            # LOCKOUT
            else:
                flash(Markup(
                    'Incorrect Credentials. Exceeded Allowed Login Attempts. <a href="/unlock">Unlock Account</a>'
                ), category='danger')
                return render_template('accounts/login.html')  # form not passed, is hidden

    return render_template('accounts/login.html', form=form)


@accounts_bp.route('/account')
def account():
    return render_template('accounts/account.html')


@accounts_bp.route('/unlock')
def unlock():
    session["login attempts"] = 0
    return redirect(url_for('accounts.login'))


@accounts_bp.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('index'))
