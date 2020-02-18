import flask
from Controllers.VideoGameController import VideoGameController
from Controllers.BookController import BookController
from Controllers.MovieController import MovieController
from Controllers.BoardGameController import BoardGameController
from Controllers.RPGController import RPGController
import concurrent.futures

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

def call_backup(controller):
    return controllers[controller].back_up_table()

@app.route('/backup', methods=['PUT'])
def backup_tables():
    response = {'failed_backups': 0, 'successful_backups': 0, 'error_messages': []}
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            backup_results = [executor.submit(call_backup, controller) for controller in controllers]
        for controller_response in concurrent.futures.as_completed(backup_results):
            result_body = controller_response.result()
            print("Received response for controller {}".format(result_body))
            if(result_body['status'] == 'FAIL'):
                response['failed_backups'] += 1
                response['error_messages'].append({'Controller': result_body['controller'], 'error_message': result_body['error_message']})
            else:
                response['successful_backups'] += 1
        json_response = flask.jsonify(response)
    except Exception as e:
        print("Exception while backing up tables: {}".format(e))
        response['error_message'] = str(e)
        json_response = flask.jsonify(response)
        json_response.status_code = 500
    return json_response

@app.route('/lib-compare/<media>/<key>', methods=['GET'])
def lookup_in_library(media, key):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code(400)
    else:
        lookup_result = controllers[media].library_compare(key)
        if(lookup_result['status'] != 'FAIL'):
            response = flask.jsonify(lookup_result)
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else 'Lookup failed')
            response.status_code = 500
    return response
"""
@app.route('/<media>')
def clear_table(media) """