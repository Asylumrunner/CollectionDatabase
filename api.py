import flask
from flask_cors import CORS
from flask import request
from Workers.MediaItemWorker import MediaItemWorker
from Workers.UsersWorker import UsersWorker
from Workers.ListWorker import ListWorker
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
    return create_response(True, 200, ["Health Check Passed!"])

def create_response(passed, status_code, data=[], err_msg=''):
    response_object = {
        'status': 'SUCCESS' if passed else 'FAILURE',
        'data': data,
        'err_msg': err_msg
    }
    response = flask.jsonify(response_object)
    response.status_code = status_code
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0')