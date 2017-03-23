from flask_mail import Message
from app import mail
from flask import render_template,current_app

def send_email(to,subject,template,**kwargs):
    msg=Message("[CodeNest]"+subject,sender=current_app.config['FLASKY_MAIL_SENDER'],recipients=[to])
    msg.body=render_template(template+'.txt',**kwargs)
    #msg.html=render_template(template+'.html',**kwargs)
    mail.send(msg)
