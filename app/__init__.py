#coding:utf-8
from flask import Flask,render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager
from log import log
from flask_pagedown import PageDown

bootstrap=Bootstrap()
pagedown=PageDown()


#flask_mail模块中提供的Mail对象,用来管理邮件
mail=Mail()

#moment可以生成一个本地格式的时间戳,在html文件中可以渲染时间相关的数据
#Example:
#   >>> import datetime from datetime
#    >>> current_time = date_time.utcnow()
#    #显示当前时间
#    >>> moment(current_time).format('LLL')
#    #显示据开始时间的时间间隔
#    >>> moment(curent_time).fromNow(refresh=True)
#    #显示中文格式的时间
#    >>> moment.lang('ch')"
moment=Moment()

#flask_sqlalchemy模块中提供的SQLAlchemy对象,用来管理数据库
db=SQLAlchemy()

#flask_login模块中的LoginManager对象,用来管理用户登录
login_manager=LoginManager()
#会话保护设置称strong
login_manager.session_protection=None
#设置视图函数
login_manager.login_view='auth.login'
#日志管理对象
log=log()

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

def create_app(config_name):
    """
    创建app的接口,接受配置名称,创建flask程序对象.
    Example:
    app=create_app('test')
    """
    app=Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    pagedown.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    
    #main\auth\api都是Blueprint对象
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint,url_prefix='/auth')
    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint,url_prefix='/api/v1.0')
    return app


