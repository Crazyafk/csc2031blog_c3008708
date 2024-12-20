import flask
import flask_login
from flask import Blueprint, render_template, flash, redirect, url_for, session
from accounts.forms import RegistrationForm, LoginForm
from config import User, db, limiter, anonymous_required, logger, ph
from markupsafe import Markup
from flask_login import login_required

accounts_bp = Blueprint('accounts', __name__, template_folder='templates')


@accounts_bp.route('/registration', methods=['GET', 'POST'])
@anonymous_required
def registration():
    form = RegistrationForm()

    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', category="danger")
            return render_template('accounts/registration.html', form=form)

        password = ph.hash(form.password.data)
        new_user = User(email=form.email.data,
                        firstname=form.firstname.data,
                        lastname=form.lastname.data,
                        phone=form.phone.data,
                        password=password,
                        )

        db.session.add(new_user)
        db.session.commit()

        new_user.generate_log()

        logger.info(f"User Registered. Email: {new_user.email} Role: {new_user.role} IP: {flask.request.remote_addr}")

        flash('Account Created. You must Set up MFA before logging in', category='success')
        return render_template('accounts/mfa.html', key=new_user.mfa_key, uri=new_user.uri)

    return render_template('accounts/registration.html', form=form)


@accounts_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20/minute')
@anonymous_required
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
            user.log.login()
            logger.info(f"Successful Login. Email: {user.email} Role: {user.role} IP: {flask.request.remote_addr}")
            flash('Authentication Success', category='success')
            return redirect(url_for('posts.posts'))

        # ----MFA SETUP----
        elif user and user.verify_password(form.password.data) and not user.mfa_enabled:
            # ----VALID LOGIN ENABLING MFA----
            if user.verify_pin(form.pin.data):
                user.mfa_enabled = True
                db.session.commit()

                flask_login.login_user(user)
                user.log.login()
                logger.info(f"Successful Login. Email: {user.email} Role: {user.role} IP: {flask.request.remote_addr}")
                flash('Authentication Success', category='success')
                return redirect(url_for('posts.posts'))

            # ----MUST SETUP MFA----
            else:
                flash('You must Set up MFA before logging in', category='success')
                return render_template('accounts/mfa.html', key=user.mfa_key, uri=user.uri)

        # ----INVALID--------
        else:
            session["login attempts"] += 1
            logger.info(f"Unsuccessful Login Attempt. Email: {user.email} Attempts Made: {session['login attempts']}"
                        f" IP: {flask.request.remote_addr}")

            # ATTEMPTS REMAINING
            if session["login attempts"] < max_login_attempts:
                flash('Incorrect Credentials. {} Attempts Remaining'.format(
                    max_login_attempts - session["login attempts"]),
                    category='danger')
                return render_template('accounts/login.html', form=form)

            # LOCKOUT
            else:
                logger.info(f"Maximum Failed Login Attempts Reached. Email: {user.email} Attempts Made: {session['login attempts']}"
                            f" IP: {flask.request.remote_addr}")
                flash(Markup(
                    'Incorrect Credentials. Exceeded Allowed Login Attempts. <a href="/unlock">Unlock Account</a>'
                ), category='danger')
                return render_template('accounts/login.html')  # form not passed, is hidden

    return render_template('accounts/login.html', form=form)


@accounts_bp.route('/account')
@login_required
def account():
    return render_template('accounts/account.html', user=flask_login.current_user)


@accounts_bp.route('/unlock')
def unlock():
    session["login attempts"] = 0
    return redirect(url_for('accounts.login'))


@accounts_bp.route('/logout')
@login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for('index'))
