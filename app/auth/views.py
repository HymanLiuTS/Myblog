#!_*_ coding:utf-8 _*_
from flask import render_template,request,redirect,url_for,flash,session,abort
from flask_login import login_user,logout_user,login_required,current_user
from . import auth
from .forms import LoginForm,RegistrationForm
from ..models import User
from app import db
from ..email import send_email


@auth.route('/login',methods=['GET','POST'])
def login():
    """
    登录控制,向服务器发送登录的表单.
    """
    form=LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.confirmed == False:
            return redirect(url_for('auth.unconfirmed',id=user.id))
        if user is not None and user.verify_password(form.password.data):
            #通过flask_login来管理登录的用户,login_user为其一个接口,用来登录
            #用户,第二个参数是一个布尔量,为True的话记住当前用户存到cookies中
            #重启浏览器后不用再重复输入用户名
            login_user(user,form.remeber_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('用户名或密码错误!')
    return render_template('auth/login.html',form=form)

@auth.route('/logout')
def logout():
    """
    登出控制,调用flask_login的logout_user()接口.
    """
    logout_user()
    #flash('退出登录成功.')
    return redirect(url_for('main.index'))


@auth.route('/register',methods=['GET','POST'])
def register():
    form=RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        #生成令牌
        user=User.query.filter_by(email=form.email.data).first()
        token=user.generate_confirmation_token()
        send_email(user.email,'Confirm your account','auth/email/confirm',user=user,token=token)
        return redirect(request.args.get('next') or url_for('auth.unconfirmed',id=user.id))
    return render_template('auth/register.html',form=form)

@auth.route('/confirm/<int:id>/<token>')
def confirm(id,token):
    user=User.query.get_or_404(id)
    if user == None:
        flash('用户尚未注册！')
        return redirect(url_for('auth.register'))
    if user.confirmed:
        flash('您已经确认过账户，无需再确认。')
        return redirect(url_for('auth.login'))
    if user.confirm(token):
        flash('账户确认完成。')
    else:
        flash('确认链接已经失效。')
        return render_template('auth/unconfirmed2.html',user=user)
    return redirect(url_for('auth.login'))

#@auth.before_app_request
"""def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5]!='auth.':
                    return redirect(url_for('auth.unconfirmed'))
"""

@auth.route('/unconfirmed/<int:id>')
def unconfirmed(id):
    user=User.query.get_or_404(id)
    if user == None:
        flash('用户尚未注册！')
        return redirect(url_for('auth.register'))
    if  user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html',user=user)

@auth.route('/confirm/<int:id>')
def resend_confirmation(id):
    user=User.query.get_or_404(id)
    if user == None:
        flash('用户尚未注册！')
        return redirect(url_for('auth.register'))
    token=user.generate_confirmation_token()
    send_email(user.email,'Confirm your account','auth/email/confirm',user=user,token=token)
    return redirect(url_for('auth.unconfirmed',id=id))

