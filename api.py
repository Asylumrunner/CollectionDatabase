import flask
from flask_cors import CORS
from flask import request
from Workers.MediaItemWorker import MediaItemWorker
from Workers.UsersWorker import UsersWorker
from Workers.ListWorker import ListWorker
from Utilities.ValidateRequestInput import validate_put_request, validate_update_request
import logging

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)

def init():
    workers = {}
    workers['MEDIAITEMS'] = MediaItemWorker()
    workers['USERS'] = UsersWorker()
    workers['LIST'] = ListWorker()
    return workers

workers = init()

@app.route('/', methods=['GET'])
def health_check():
    response = flask.jsonify("We're Good!")
    response.status_code = 200
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0')