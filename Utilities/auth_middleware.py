import os
import logging
from functools import wraps
from flask import request, jsonify, g
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

# Initialize logger
logger = logging.getLogger(__name__)

def get_clerk_client() -> Clerk:
    clerk_secret = os.environ.get('CLERK_SECRET_KEY')

    if not clerk_secret:
        try:
            from Workers.secrets import secrets
            clerk_secret = secrets.get('Clerk_Secret_Key')
        except ImportError:
            logger.error("Failed to import secrets.py")

    if not clerk_secret:
        raise RuntimeError("CLERK_SECRET_KEY not found in environment or secrets.py")

    return Clerk(bearer_auth=clerk_secret)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({
                'status': 'FAILURE',
                'data': [],
                'err_msg': 'Missing Authorization header',
                'error_code': 'AUTH_MISSING_HEADER'
            }), 401

        # Expected format: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning(f"Invalid Authorization header format")
            return jsonify({
                'status': 'FAILURE',
                'data': [],
                'err_msg': 'Invalid Authorization header format. Expected: Bearer <token>',
                'error_code': 'AUTH_INVALID_FORMAT'
            }), 401

        token = parts[1]

        try:
            sdk = get_clerk_client()

            request_state = sdk.authenticate_request(
                request,
                AuthenticateRequestOptions()
            )

            if not request_state.is_signed_in:
                reason = getattr(request_state, 'reason', 'Authentication failed')
                logger.warning(f"Authentication failed: {reason}")
                return jsonify({
                    'status': 'FAILURE',
                    'data': [],
                    'err_msg': f'Authentication failed: {reason}',
                    'error_code': 'AUTH_VERIFICATION_FAILED'
                }), 401

            # Extract user information from the token payload
            payload = request_state.payload

            # Store user info in Flask's g object for access in the route
            g.user_id = payload.get('sub')  # Subject claim = user ID
            g.user_email = payload.get('email')
            g.user_info = {
                'user_id': payload.get('sub'),
                'email': payload.get('email'),
                'email_verified': payload.get('email_verified'),
                'first_name': payload.get('first_name'),
                'last_name': payload.get('last_name'),
                'username': payload.get('username'),
                'session_id': payload.get('sid'),
                'issued_at': payload.get('iat'),
                'expires_at': payload.get('exp'),
            }

            logger.info(f"Authenticated request from user: {g.user_id}")

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'FAILURE',
                'data': [],
                'err_msg': 'Authentication failed',
                'error_code': 'AUTH_INTERNAL_ERROR'
            }), 401

        return f(*args, **kwargs)

    return decorated_function
