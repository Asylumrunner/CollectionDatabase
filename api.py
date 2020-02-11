import flask
from VideoGameController import VideoGameController
#from BookController import BookController
from MovieController import MovieController
from BoardGameController import BoardGameController
from RPGController import RPGController

app = flask.Flask(__name__)
app.config['DEBUG'] = True

def init():
    controller_dict = {}
    #controller_dict['books'] = BookController()
    controller_dict['movies'] = MovieController()
    controller_dict['video_game'] = VideoGameController()
    controller_dict['board_game'] = BoardGameController()
    controller_dict['rpg'] = RPGController()
    return controller_dict

controllers = init()

@app.route('/lookup/<media>/<title>', methods=['GET'])
def lookup_data(media, title):
    if media not in controllers:
        return flask.jsonify('Invalid media type')
    else:
        return flask.jsonify(controllers[media].lookup_entry(title))

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
            response.status_code = 400
    return response
"""
@app.route('/<media>/<key>')
def get_entry(media, key):
    return 200

@app.route('/<media>/<key>')
def delete_entry(media, key)

@app.route('/<media>')
def get_table(media)

@app.route('/<media>')
def clear_table(media) """