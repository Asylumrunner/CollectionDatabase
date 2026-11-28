import logging
import flask
from flask import g

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get("request_id", "-") if flask.has_app_context() else "-"
        return True

def configure_logging():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s')
    # urllib3 logs every request URL, query string included, at DEBUG. TMDB and Discogs take their API
    # keys as query parameters, so keep it quiet whatever level the rest of the app runs at
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())
