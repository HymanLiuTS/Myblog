#coding:utf-8

from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField
from wtforms.validators import Required,Length,Email,Regexp,EqualTo,ValidationError
from ..models import User
from flask import current_app
from flask_login import current_user
class LoginForm(FlaskForm):
    """
    登录表单
    """
    email=StringField('电子邮箱:',validators=[Required(),Length(1,64),Email()])
    password=PasswordField('密码:',validators=[Required()])
    remeber_me=BooleanField('记住用户名和密码')
    submit=SubmitField('登录')

class RegistrationForm(FlaskForm):
    email=StringField('电子邮箱:',validators=[Required(),Length(1,64),Email()])
    username=StringField('用户名:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'用户名只能含有字母、数字、点和下划线')])
    password=PasswordField('密码:',validators=[Required(),EqualTo('password2',message='两次输入的密码不一致。')])
    password2=PasswordField('密码确认:',validators=[Required()])
    submit=SubmitField('注册')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email已经被注册。')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已经被使用。')

class ChangePWForm(FlaskForm):
    """
    修改用户密码的表单
    """
    email = StringField('电子邮箱:', validators=[Required(), Length(1, 64), Email()])
    password = PasswordField('新密码:', validators=[Required(), EqualTo('password2', message='两次输入的密码不一致。')])
    password2 = PasswordField('密码确认:', validators=[Required()])
    submit = SubmitField('确认修改')

    def validate_email(self,field):
        if current_user.email != field.data:
            raise  ValidationError('请输入当前用户的Email。')
        


