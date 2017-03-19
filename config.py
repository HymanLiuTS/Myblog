#coding:utf-8
#重新设置系统的默认编码格式
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    config基类,用来设置公有的配置参数.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    FLASKY_MAIL_SUBJECT_PREFIX='[Flasky]'
    FLASKY_MAIL_SENDER = 'codenest@codenest.cn'
    FLASKY_ADMIN = '879651072@qq.com'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    FLASK_POSTS_PRE_PAGE=10
    FLASKY_FOLLOWERS_PER_PAGE=50
    FLASKY_COMMENTS_PER_PAGE=10
    UPLOAD_PATH='/Github/Myblog/app/static/images'
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """
    开发环境配置
    """
    DEBUG = True
    MAIL_SERVER = 'mail.codenest.cn'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'codenest@codenest.cn'#os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = ''#os.environ.get('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI') or \
            'sqlite:///' + os.path.join(basedir,'data-dev.sqlite')

class TestingConfig(Config):
    """
    测试环境配置
    """
    TESTING = False
    WTF_CRSF_ENABLED=False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI') or \
            'sqlite:///' + os.path.join(basedir,'data-test.sqlite')

class ProductionConfig(Config):
    """
    生产环境配置
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
            'sqlite:///' + os.path.join(basedir,'data.sqlite')

#用来根据不同配置字符串生成对应配置对象的字典
config={
        'development':DevelopmentConfig,
        'testing':TestingConfig,
        'production':ProductionConfig,
        'default':DevelopmentConfig
        }

