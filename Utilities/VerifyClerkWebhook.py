from svix.webhooks import Webhook, WebhookVerificationError
from Workers.secrets import secrets
from flask import request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def verify_clerk_webhook(f):
    """
    Decorator to verify Clerk webhook signatures using Svix.

    Extracts the svix-id, svix-timestamp, and svix-signature headers
    and verifies the payload against the CLERK_WEBHOOK_SECRET.

    On success, passes the verified payload to the decorated function.
    On failure, returns a 400 response.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get the raw payload
            payload = request.get_data(as_text=True)

            # Get Svix headers
            headers = {
                "svix-id": request.headers.get("svix-id"),
                "svix-timestamp": request.headers.get("svix-timestamp"),
                "svix-signature": request.headers.get("svix-signature"),
            }

            # Check all required headers are present
            missing_headers = [k for k, v in headers.items() if not v]
            if missing_headers:
                logger.warning(f"Missing webhook headers: {missing_headers}")
                return jsonify({
                    'status': 'FAILURE',
                    'err_msg': f"Missing required headers: {', '.join(missing_headers)}"
                }), 400

            # Verify the webhook signature
            webhook_secret = secrets.get('CLERK_WEBHOOK_SECRET')
            if not webhook_secret:
                logger.error("CLERK_WEBHOOK_SECRET not configured")
                return jsonify({
                    'status': 'FAILURE',
                    'err_msg': "Webhook secret not configured"
                }), 500

            wh = Webhook(webhook_secret)
            verified_payload = wh.verify(payload, headers)

            # Pass the verified payload to the handler
            kwargs['payload'] = verified_payload
            return f(*args, **kwargs)

        except WebhookVerificationError as e:
            logger.warning(f"Webhook verification failed: {e}")
            return jsonify({
                'status': 'FAILURE',
                'err_msg': "Invalid webhook signature"
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error verifying webhook: {e}")
            return jsonify({
                'status': 'FAILURE',
                'err_msg': "Error processing webhook"
            }), 500

    return decorated_function
