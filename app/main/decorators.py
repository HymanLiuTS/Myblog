from functools import wraps
from flask import abort
from flask_login import current_user
from ..models import Permission
from app import log
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorator_function(*args,**kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args,**kwargs)
        return decorator_function
    return decorator

def admin_required(f):
    log.write('admin_required','admin_required')
    return permission_required(Permission.ADMINISTER)(f)

