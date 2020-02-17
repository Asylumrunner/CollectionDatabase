import flask
from VideoGameController import VideoGameController
from BookController import BookController
from MovieController import MovieController
from BoardGameController import BoardGameController
from RPGController import RPGController

app = flask.Flask(__name__)
app.config['DEBUG'] = True

def init():
    controller_dict = {}
    controller_dict['books'] = BookController()
    controller_dict['movies'] = MovieController()
    controller_dict['video_game'] = VideoGameController()
    controller_dict['board_game'] = BoardGameController()
    controller_dict['rpg'] = RPGController()
    return controller_dict

controllers = init()

@app.route('/lookup/<media>/<title>', methods=['GET'])
def lookup_data(media, title):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        lookup_response = controllers[media].lookup_entry(title)
        if('Exception' in lookup_response[0]):
            response = flask.jsonify(lookup_response[0]['Exception'])
            response.status_code = 500
        else:
            response = flask.jsonify(lookup_response)
    return response

@app.route('/<media>/<key>', methods=['PUT'])
def put_entry(media, key):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        if(controllers[media].put_key(key)):
            response = flask.jsonify('Key {} successfully inserted'.format(key))
        else:
            response = flask.jsonify('Insert failed')
            response.status_code = 500
    return response

@app.route('/<media>/<key>', methods=['GET'])
def get_entry(media, key):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        lookup_result = controllers[media].get_key(key)
        if(lookup_result['status'] != 'FAIL'):
            response = flask.jsonify(lookup_result['item'])
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
    return response

@app.route('/<media>/<key>', methods=['DELETE'])
def delete_entry(media, key):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        lookup_result = controllers[media].delete_key(key)
        if(lookup_result['status'] != 'FAIL'):
            response = flask.jsonify(lookup_result['item'])
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
    return response

@app.route('/<media>', methods=['GET'])
def get_table(media):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        lookup_result = controllers[media].get_table()
        if('Items' in lookup_result and 'error_message' not in lookup_result):
            response = flask.jsonify(lookup_result['Items'])
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
    return response
"""
@app.route('/<media>')
def clear_table(media) """