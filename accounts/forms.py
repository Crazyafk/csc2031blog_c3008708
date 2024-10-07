import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
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

class RegistrationForm(FlaskForm):
    email = StringField(validators=[DataRequired()])
    firstname = StringField(validators=[DataRequired()])
    lastname = StringField(validators=[DataRequired()])
    phone = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired(), StrongPassword])
    confirm_password = PasswordField(validators=[DataRequired(), EqualTo('password', message='Both password fields must be equal!')])
    submit = SubmitField()

class LoginForm(FlaskForm):
    email = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])
    submit = SubmitField()