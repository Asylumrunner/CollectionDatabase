import requests
from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json
import pprint

class VideoGameController(GenreController):
    
    def __init__(self):
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"
        self.game_key_req_template = "https://www.giantbomb.com/api/game/{}/?api_key={}&format=json"
        self.guid_prefix = "VG-"
        super().__init__()

    def lookup_entry(self, title, picky=False):
        try:
            req = requests.get(self.lookup_req_template.format(self.GB_API_KEY, title), headers=self.header).json()
            response = []
            for game in req['results']:
                platforms = [platform['name'] for platform in game['platforms']] if game['platforms'] else ""
                response.append({'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': platforms})
            if picky:
                best_game = self.fuzzy_string_match(title, [game['name'] for game in response])
                response = [game for game in response if game['name'] == best_game[0]]
        except Exception as e:
            print("Exception in lookup for title {} in VideoGameController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def put_key(self, key):
        try:
            req = requests.get(self.game_key_req_template.format(key, self.GB_API_KEY), headers=self.header)
            if(req.status_code == 200 and req.json()['error'] == 'OK'):
                game = req.json()['results']
                print([platform['name'] for platform in game['platforms']])
                response = self.dynamodb.put_item(
                    Item={
                        'guid': self.guid_prefix + game['guid'],
                        'original_guid': game['guid'],
                        'name': game['name'],
                        'release_year': game['original_release_date'][:4] if game['original_release_date'] else game['expected_release_year'],
                        'platform': [platform['name'] for platform in game['platforms']],
                        'summary': game['deck']
                    }
                )
                print(response)
                return True
            else:
                return False
        except Exception as e:
            print("Exception while putting key {} in database via VideoGameController: {}".format(key, e))
            return False

