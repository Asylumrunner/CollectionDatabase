from Workers.secrets import secrets
from clerk_backend_api import Clerk, ClerkError
from clerk_backend_api.security.types import AuthenticateRequestOptions
import sys
import traceback
import pprint

def is_signed_in(request):
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
        pprint.pprint(request_state)
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
        print("We are indeed signed in!")
        return request_state
    else:
        print("We are not signed in, throwing error")
        raise ClerkError("Request not authenticated")