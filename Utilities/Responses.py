import flask
from dataclasses import asdict


def create_response(passed, status_code, page, data=[], err_msg=''):
    response_object = {
        'status': 'SUCCESS' if passed else 'FAILURE',
        'data': data,
        'err_msg': err_msg,
        'next_page': page
    }
    response = flask.jsonify(response_object)
    response.status_code = status_code
    return response


def public_error_message(failure):
    # Worker failure objects hold tracebacks and call arguments (including user IDs), which stay
    # in the server logs. Clients only get the step that failed.
    step = failure.get('step_failed') if isinstance(failure, dict) else None
    return f"Internal server error at step '{step}'" if step else "Internal server error"


def worker_failure(failure):
    return create_response(False, 500, None, [], public_error_message(failure))


def respond(result, key=None, not_found_msg=None):
    """Turns a worker result into a response: a 500 if the worker failed, a 404 if not_found_msg is
    given and the worker found nothing, otherwise a 200 carrying result[key], or the whole result
    when no key is given."""
    if not result['passed']:
        return worker_failure(result)
    if not_found_msg and result['not_found']:
        return create_response(False, 404, None, [], not_found_msg)
    return create_response(True, 200, None, result[key] if key else result)


def respond_with_page(result, not_found_msg=None):
    """As respond, for worker results holding a page of Items and the number of the next page."""
    if not result['passed']:
        return worker_failure(result)
    if not_found_msg and result['not_found']:
        return create_response(False, 404, None, [], not_found_msg)
    return create_response(True, 200, result['next_page'], [asdict(item) for item in result['items']])
