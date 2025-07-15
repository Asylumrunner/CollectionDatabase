import logging
from wtforms import Form, StringField, IntegerField, validators

def fail_because(reason_string):
    response = {
        'valid': False,
        'reason': reason_string
    }
    logging.error(reason_string)
    return response