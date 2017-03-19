from flask_httpauth import HTTPBasicAuth
from ..models import User,AnonymousUser
from .import api
from .errors import forbidden
from flask import g,jsonify

auth=HTTPBasicAuth()

@auth.verify_password
def vertify_password(email,password):
    if email=='':
        g.current_user=AnonymousUser()
        return True
    if password=='':
        g.current_user=User.vertify_auth_token(email_or_token)
        g.token_used=True
        return g.current_user is not None
    user=User.query.filter_by(email=email).first()
    if not user:
        return False
    g.current_user=user
    g.token_used=False
    return user.verify_password(password)

@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')

@api.route('/posts/')
@auth.login_required
def get_posts():
    pass

@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and not g.current_user.confirm:
        return forbidden('UNconfirmed account')

@api.route('/token')
def get_token():
    if g.current_user.is_anonymous() or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token':g.current_user.generate_auth_token(expiration=3600),'expiration':3600})

@api.route('/posts/',methods=['POST'])
def new_post():
    post=Post.from_json(request.json)
    post.author=g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())
