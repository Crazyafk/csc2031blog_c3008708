import re
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, EqualTo, ValidationError


def StrongPassword(form, field):
    if len(field.data) < 8 or len(field.data) > 15:
        raise ValidationError('Password must be 8-15 characters long')
    if not re.search(r"[a-z]", field.data):
        raise ValidationError('Password must contain at least 1 lowercase letter')
    if not re.search(r"[A-Z]", field.data):
        raise ValidationError('Password must contain at least 1 uppercase character')
    if not re.search(r"[0-9]", field.data):
        raise ValidationError('Password must contain at least 1 digit')
    if not re.search(r"[^A-Za-z0-9]", field.data):
        raise ValidationError('Password must contain at least 1 special character')

def LettersOrHyphen(form, field):
    if not re.search(r"^[a-zA-Z-]+$", field.data):
        raise ValidationError('String must contain only Letters or Hyphens')

def UKLandline(form, field):
    if not re.search(r"(^02\d-\d{8,8}$)|(^011\d-\d{7,7}$)|(^01\d1-\d{7,7}$)|(^01\d{3,3}-\d{5,6}$)", field.data):
        raise ValidationError('Phone number must be a valid UK landline')


class RegistrationForm(FlaskForm):
    email = EmailField(validators=[DataRequired()])
    firstname = StringField(validators=[DataRequired(), LettersOrHyphen])
    lastname = StringField(validators=[DataRequired(), LettersOrHyphen])
    phone = StringField(validators=[DataRequired(), UKLandline])
    password = PasswordField(validators=[DataRequired(), StrongPassword])
    confirm_password = PasswordField(validators=[DataRequired(), EqualTo('password', message='Both password fields must be equal!')])
    submit = SubmitField()

class LoginForm(FlaskForm):
    email = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])
    pin = StringField(validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField()