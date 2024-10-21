from flask import Blueprint, render_template, flash, redirect, url_for, session
from accounts.forms import RegistrationForm, LoginForm
from config import User, db
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

        flash('Account Created', category='success')
        return redirect(url_for('accounts.login'))

    return render_template('accounts/registration.html', form=form)


@accounts_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    max_login_attempts = 3

    if not session.get("login attempts"):
        session["login attempts"] = 0

    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()

        # ----VALID LOGIN----
        if user and user.verify_password(form.password.data):
            flash('Authentication Success', category='success')
            return redirect(url_for('posts.posts'))

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
