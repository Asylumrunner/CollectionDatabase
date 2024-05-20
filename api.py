import flask
from flask_cors import CORS
from flask import request
from Controllers.VideoGameController import VideoGameController
from Controllers.BookController import BookController
from Controllers.MovieController import MovieController
from Controllers.BoardGameController import BoardGameController
from Controllers.RPGController import RPGController
from Controllers.AnimeController import AnimeController
from Controllers.MusicController import MusicController
from Workers.SearchWorker import SearchWorker
from Workers.DbGetWorker import DbGetWorker
from Workers.DbDeleteWorker import DbDeleteWorker
import logging
import concurrent.futures

app = flask.Flask(__name__)
app.config['DEBUG'] = True
CORS(app)
search_worker = SearchWorker()
db_get_worker = DbGetWorker()
db_delete_worker = DbDeleteWorker()

def init():
    
    controller_dict = {}
    controller_dict['book'] = BookController()
    controller_dict['movie'] = MovieController()
    controller_dict['video_game'] = VideoGameController()
    controller_dict['board_game'] = BoardGameController()
    controller_dict['rpg'] = RPGController()
    controller_dict['anime'] = AnimeController()
    controller_dict['music'] = MusicController()
    return controller_dict

controllers = init()

@app.route('/search/<title>', methods=['GET'])
def lookup_data(title):
    media_type = request.args.get("media_type")
    logging.info(f'media_type provided with search request {media_type}')
    if media_type == None:
        logging.error("No media_type provided with request")
        response = flask.jsonify("No media_type provided")
        response.status_code = 500
        return response
    
    lookup_response = search_worker.search_item(title, media_type)

    if('Exception' in lookup_response[0]):
        response = flask.jsonify(lookup_response[0]['Exception'])
        response.status_code = 500
    else:
        response = flask.jsonify(lookup_response)
    return response

@app.route('/lookup/bulk/<media>', methods=['GET'])
def bulk_lookup_data(media):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        request_dict = flask.request.get_json()
        if "titles" not in request_dict:
            response = flask.jsonify("No titles found. Please insert titles as list under key \'titles\'")
            response.status_code = 400
        else:
            total_results = []
            picky = "picky" in request_dict and request_dict["picky"]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = [executor.submit(controllers[media].lookup_entry, title, picky) for title in request_dict['titles']]
            for lookup in concurrent.futures.as_completed(lookups):
                total_results.append(lookup.result())
            response = flask.jsonify(total_results)
    return response


@app.route('/<media>/<key>', methods=['POST'])
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

@app.route('/<media>/bulk', methods=['POST'])
def put_entries_bulk(media):
    if media not in controllers:
        response = flask.jsonify('Invalid media type')
        response.status_code = 400
    else:
        request_dict = flask.request.get_json()
        total_inserts = len(request_dict['keys'])
        successful_inserts = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            inserts = [executor.submit(controllers[media].put_key, key) for key in request_dict['keys']]
        for insert in concurrent.futures.as_completed(inserts):
            if insert:
                successful_inserts += 1
        response = flask.jsonify("{} out of {} keys successfully submitted".format(successful_inserts, total_inserts))
    return response

@app.route('/item/<key>', methods=['GET'])
def get_entry(key):
    lookup_result = db_get_worker.get_item(key)
    if(lookup_result['status'] != 'FAIL'):
        response = flask.jsonify(lookup_result['item']) if 'item' in lookup_result else {}
    else:
        response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Get failed")
        response.status_code = 500
    return response

@app.route('/item/<key>', methods=['PUT'])
def update_entry(key):
    

@app.route('/item/<key>', methods=['DELETE'])
def delete_entry(key):
    delete_result = db_delete_worker.delete_item(key)
    if(delete_result['status'] != 'FAIL'):
        response = flask.jsonify(delete_result['item']) if 'item' in delete_result else {}
    else:
        response = flask.jsonify(delete_result['error_message'] if 'error_message' in delete_result else "Delete failed")
        response.status_code = 500
    return response

@app.route('/collection', methods=['GET'])
def get_every_table():
    excluded_controllers = request.args.getlist('included_items')
    total_response = {}
    for controller_type in [key for key in controllers.keys() if key not in excluded_controllers]:
        lookup_result = controllers[controller_type].get_table()
        if('Items' in lookup_result and 'error_message' not in lookup_result):
            total_response[controller_type] = lookup_result['Items']
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
            return response
    response = flask.jsonify(total_response)
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

def call_restore(controller):
    return controllers[controller].back_up_table()

@app.route('/restore', methods=['PUT'])
def restore_tables():
    response = {'failed_restores': 0, 'successful_restores': 0, 'error_messages': []}
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            restore_results = [executor.submit(call_restore, controller) for controller in controllers]
        for controller_response in concurrent.futures.as_completed(restore_results):
            result_body = controller_response.result()
            print("Received response for controller {}".format(result_body))
            if(result_body['status'] == 'FAIL'):
                response['failed_restores'] += 1
                response['error_messages'].append({'Controller': result_body['controller'], 'error_message': result_body['error_message']})
            else:
                response['successful_restores'] += 1
        json_response = flask.jsonify(response)
    except Exception as e:
        print("Exception while backing up tables: {}".format(e))
        response['error_message'] = str(e)
        json_response = flask.jsonify(response)
        json_response.status_code = 500

@app.route('/lib-compare/<media>', methods=['GET'])
@app.route('/lib-compare/<media>/<key>', methods=['GET'])
def lookup_in_library(media, key=None):
    if media != 'books':
        response = flask.jsonify('Invalid media type')
        response.status_code(400)
    elif not key:
        table_get_result = controllers[media].get_table()
        if('Items' in table_get_result and 'error_message' not in table_get_result):
            items = table_get_result['Items']
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookup_results = [executor.submit(controllers[media].library_compare, key) for key in [item['original_guid'] for item in items]]

            results = {"lookup_results": []}
            for controller_response in concurrent.futures.as_completed(lookup_results):
                results['lookup_results'].append(controller_response.result())
            response = flask.jsonify(results)
        else:
            response = flask.jsonify(lookup_result['error_message'] if 'error_message' in lookup_result else "Lookup failed")
            response.status_code = 500
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