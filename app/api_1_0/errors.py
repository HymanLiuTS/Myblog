from flask import jsonify
from app.exceptions import ValidationError
from . import api
def forbidden(message):
    response=jsonify({'error':'forbidden','message':message})
    response.status_code=403
    return response

@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])
