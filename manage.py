#!/usr/bin/env python
#coding:utf-8

import os
from app import create_app,db
from app.models import User,Role,Post,RunningInfo,Visitor
from flask_script import Manager,Shell
from flask_migrate import Migrate,MigrateCommand
from momentjs import momentjs
from datetime import datetime
from flask import request

COV=None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV=coverage.coverage(branch=True,include='app/*')
    COV.start()

app=create_app(os.getenv('FLASK_CONFIG') or 'default')

manager=Manager(app)
"""
创建manage对象,该对象以flask的程序app为参数创建,后续进行
app的管理,使启动服务器时支持命令行.
Example:
    开启服务器:python manage.py runserver
"""

migrate=Migrate(app,db)
"""
创建migrate对象,用来管理数据库的迁移等相关工作,Migrate接受两个参数
一个是flask的程序对象app,一个是SQLAlchemy数据库管理对象
"""

def make_shell_context():
    return dict(app=app,db=db,User=User,Role=Role,Post=Post)

manager.add_command("shell",Shell(make_context=make_shell_context))
manager.add_command('db',MigrateCommand)

@manager.command
def test():
    """单元测试"""
    import unittest
    tests=unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

@manager.command
def myprint():
    print 'hello world'

"""
@manager.command
def test1(coverage=False):
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE']='1'
        os.execvp(sys.executable,[sys.executable]+sys.argv)
    import unittest
    test=unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(test)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary')
        COV.report()
        basedir=os.path.abspath(os.path.dirname(__file__))
        covdir=os.path.join(basedir,'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version:file://%s/index.html'%covdir)
        COV.erase()
"""
@manager.command
def deploy():
    """部署"""
    from flask_migrate import upgrade
    from app.models import Role,User,Group,Tag
    upgrade()
    Role.insert_roles()
    User.add_self_follows()
    Group.insert_groups()
    Tag.insert_tags()

@app.before_request
def record_vistors():
    running_info = RunningInfo.query.first();
    now=datetime.utcnow()
    if running_info == None:
        running_info=RunningInfo(vistors=0)
    ipaddr=request.remote_addr
    visitor=Visitor.query.filter_by(visitor_ip=ipaddr).first()
    if(visitor==None):
        visitor=Visitor(visitor_ip=ipaddr,visit_counts=0)
        running_info.vistors=running_info.vistors+1
    else:
        if (now - visitor.last_visit_time).days>0:
            running_info.vistors=running_info.vistors+1
    visitor.visit_counts=visitor.visit_counts+1
    visitor.last_visit_time=now    
    db.session.add(running_info)
    db.session.add(visitor)
    

#app.jinja_env.globals['momentjs'] = momentjs

if __name__=='__main__':
    manager.run()
