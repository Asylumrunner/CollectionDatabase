from svix.webhooks import Webhook, WebhookVerificationError
from Workers.secrets import secrets
from Utilities.Responses import create_response
from flask import request
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
                return create_response(False, 400, None, [], f"Missing required headers: {', '.join(missing_headers)}")

            # Verify the webhook signature
            webhook_secret = secrets.get('CLERK_WEBHOOK_SECRET')
            if not webhook_secret:
                logger.error("CLERK_WEBHOOK_SECRET not configured")
                return create_response(False, 500, None, [], "Webhook secret not configured")

            wh = Webhook(webhook_secret)
            verified_payload = wh.verify(payload, headers)

        except WebhookVerificationError as e:
            logger.warning(f"Webhook verification failed: {e}")
            return create_response(False, 400, None, [], "Invalid webhook signature")
        except Exception as e:
            logger.error(f"Unexpected error verifying webhook: {e}")
            return create_response(False, 500, None, [], "Error processing webhook")

        # Separate from the try above so handler errors aren't reported as verification failures
        kwargs['payload'] = verified_payload
        try:
            return f(*args, **kwargs)
        except Exception:
            logger.exception("Webhook handler failed")
            return create_response(False, 500, None, [], "Error processing webhook")

    return decorated_function
