from Workers.secrets import secrets
from Utilities.ExceptionStack import exception_stack
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from flask import request, jsonify
from functools import wraps
import logging
import os

logger = logging.getLogger(__name__)

# Clerk rejection reasons that point at a problem on our side (configuration, or Clerk's signing keys)
# rather than at the request, so they're logged as errors. Every other reason is a bad, expired or
# missing token, which is routine and logged as a warning
_SERVER_SIDE_REASONS = {"secret-key-missing", "jwk-failed-to-load", "jwk-remote-invalid", "jwk-failed-to-resolve", "server-error"}

_skip_auth_warned = False


class NotAuthenticated(Exception):
    """The request didn't carry a valid Clerk session."""


def is_signed_in(request):
    if os.environ.get('SKIP_AUTH'):
        _warn_auth_skipped()
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
    except Exception as e:
        # Clerk couldn't check the request at all, as opposed to rejecting it: it's unreachable, or the
        # secret key is missing. The message is left out since it can carry request details
        logger.error(f"Authentication check failed: error_type={type(e).__name__} stack={exception_stack(e)}")
        raise

    # A rejected request has no payload, so this has to be checked before reading the user ID from it
    if not request_state.is_signed_in:
        reason = _reason_code(request_state)
        log = logger.error if reason in _SERVER_SIDE_REASONS else logger.warning
        log(f"Request not authenticated: reason={reason}")
        raise NotAuthenticated("Request not authenticated")

    user = (request_state.payload or {}).get('sub')
    if not user:
        logger.warning("Request not authenticated: reason=missing-subject")
        raise NotAuthenticated("Request not authenticated")
    return user


def _reason_code(request_state):
    # Clerk's reasons are enums whose value is a (code, description) pair, such as
    # ('token-expired', 'Token has expired...'). Only the code is logged
    reason = getattr(request_state, 'reason', None)
    if reason is None:
        return "unknown"
    value = getattr(reason, 'value', reason)
    return value[0] if isinstance(value, tuple) else str(value)


def _warn_auth_skipped():
    # Logged once per process rather than per request. The dev user's ID isn't logged, since it's a real Clerk ID
    global _skip_auth_warned
    if not _skip_auth_warned:
        logger.warning("SKIP_AUTH is set: authentication is disabled and every request runs as DEV_USER_ID")
        _skip_auth_warned = True


def authenticated_endpoint(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract the user_id from the response from Clerk
            # rather than accepting it explicitly, then
            # return that to the view
            # NOTE: this is the CLERK ID, not the username
            user_id = is_signed_in(request)
        except Exception:
            # is_signed_in has already logged why. The client gets a generic message, since the
            # exception text can describe server internals
            response_object = {
                'status': 'FAILURE',
                'data': [],
                'err_msg': 'Not authenticated',
                'next_page': ''
            }
            response = jsonify(response_object)
            response.status_code = 401
            return response

        # Called outside the try so that errors raised by the view itself
        # propagate normally instead of being reported as 401 Unauthorized
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    return decorated_function
