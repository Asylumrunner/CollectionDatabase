from Workers.secrets import secrets
from clerk_backend_api import Clerk, ClerkError
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import request, jsonify
from functools import wraps
import sys
import traceback
import pprint
import os

def is_signed_in(request):
    if os.environ.get('SKIP_AUTH'):
        return os.environ.get('DEV_USER_ID', 'test_user_dev')

    try:
        clerk = Clerk(bearer_auth=secrets['CLERK_SECRET_KEY'])
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=[
                    'http://localhost:8080'
                ]
            )
        )
        user = request_state.payload.get('sub', None)
    except Exception as e:
        _exc_type, _exc_value, exc_traceback = sys.exc_info()

        pprint.pprint({
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "traceback_lines": traceback.format_tb(exc_traceback),
            "exception_args": e.args if hasattr(e, 'args') else None
        })
        raise e

    if request_state.is_signed_in:
        return user
    else:
        raise ClerkError("Request not authenticated")

def authenticated_endpoint(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = is_signed_in(request)
            kwargs['user_id'] = user_id
            return f(*args, **kwargs)
        except Exception as e:
            response_object = {
                'status': 'FAILURE',
                'data': [],
                'err_msg': str(e),
                'next_page': ''
            }
            response = jsonify(response_object)
            response.status_code = 401
            return response
    return decorated_function