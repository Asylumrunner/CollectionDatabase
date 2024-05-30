import logging

def validate_put_request(request):
    valid_media_types = ['album', 'anime', 'board_game', 'book', 'movie', 'rpg', 'video_game']

    valid_field_names = {
        'album': ['title', 'media_type', 'release_year', 'img_link', 'duration', 'created_by', 'finished'],
        'anime': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'num_episodes', 'created_by', 'finished'],
        'board_game': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'min_players', 'max_players', 'finished'],
        'book': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'movie': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'language', 'finished'],
        'rpg': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'video_game': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'platforms', 'finished']
    }
    if 'title' not in request:
        return fail_because('Request must include \'title\' field')
    
    if 'media_type' not in request:
        return fail_because('Request must include \'media_type\' field')
    
    type = request['media_type']
    if type not in valid_media_types:
        return fail_because(f'\'media_type\' {type} invalid, please use one of {valid_media_types}')
    
    invalid_fields = [field for field in request if field not in valid_field_names[type]]

    if invalid_fields:
        return fail_because(f'For \'media_type\' {type}, fields {invalid_fields} are unknown')
    
    return {
        'valid': True
    }

def validate_update_request(request):
    valid_media_types = ['album', 'anime', 'board_game', 'book', 'movie', 'rpg', 'video_game']

    valid_field_names = {
        'album': ['title', 'media_type', 'release_year', 'img_link', 'duration', 'created_by', 'finished'],
        'anime': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'num_episodes', 'created_by', 'finished'],
        'board_game': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'min_players', 'max_players', 'finished'],
        'book': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'movie': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'duration', 'created_by', 'language', 'finished'],
        'rpg': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'finished'],
        'video_game': ['title', 'media_type', 'release_year', 'img_link', 'summary', 'created_by', 'platforms', 'finished']
    }

    if 'media_type' not in request:
        return fail_because('Request must include \'media_type\' field')
    
    type = request['media_type']
    if type not in valid_media_types:
        return fail_because(f'\'media_type\' {type} invalid, please use one of {valid_media_types}')
    
    invalid_fields = [field for field in request if field not in valid_field_names[type]]

    if invalid_fields:
        return fail_because(f'For \'media_type\' {type}, fields {invalid_fields} are unknown')
    
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