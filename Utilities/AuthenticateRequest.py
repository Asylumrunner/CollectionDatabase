from ..Workers.secrets import secrets
from clerk_backend_api import Clerk, ClerkError
from clerk_backend_api.security.types import AuthenticateRequestOptions

def is_signed_in(request):
    clerk = Clerk(bearer_auth=secrets['CLERK_SECRET_KEY'])
    request_state = clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=[
                'localhost:8080'
            ]
        )
    )

    if request_state.is_signed_in:
        return request_state
    else:
        raise ClerkError("Request not authenticated")