import logging

def validate_put_request(request):
    valid_media_types = ['album', 'anime', 'board_game', 'book', 'movie', 'rpg', 'video_game']

    valid_field_names = {
        'album': ['name', 'media_type', 'release_year', 'img_link', 'duration', 'created_by', 'finished'],
        'anime': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'num_episodes', 'created_by', 'finished'],
        'board_game': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'min_players', 'max_players', 'finished'],
        'book': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'movie': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'language', 'finished'],
        'rpg': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'video_game': ['name', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'platforms', 'finished']
    }
    if 'name' not in request:
        return fail_because('Request must include \'name\' field')
    
    if 'media_type' not in request:
        return fail_because('Request must include \'media_type\' field')
    
    if request['media_type'] not in valid_media_types:
        return fail_because(f'\'media_type\' {request['media_type']} invalid, please use one of {valid_media_types}')
    
    invalid_fields = [field for field in request if field not in valid_field_names[request['media_type']]]

    if invalid_fields:
        return fail_because(f'For \'media_type\' {request['media_type']}, fields {invalid_fields} are unknown')
    
    return {
        'valid': True
    }

def fail_because(reason_string):
    response = {
        'valid': False,
        'reason': reason_string
    }
    logging.error(reason_string)
    return response