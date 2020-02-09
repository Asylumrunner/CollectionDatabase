import requests
import boto3
from secrets import secrets
from genre_controller import GenreController

class VideoGameController(GenreController):
    
    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY'],)
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"
        self.game_key_req_template = "https://www.giantbomb.com/api/game/{}/?api_key={}&format=json"

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.GB_API_KEY, title), headers=self.header)
        response = [{'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': [platform['name'] for platform in game['platforms']]} for game in req.json()['results']]
        return response
    
    def put_key(self, key):
        req = requests.get(self.game_key_req_template.format(key, self.GB_API_KEY), headers=self.header)
        if(req.status_code == 200 and req.json()['error'] == 'OK'):
            game = req.json()['results']
            response = self.dynamodb.put_item(
                TableName='CollectionTable',
                Item={
                    'guid': {'S': game['guid']},
                    'name': {'S': game['name']},
                    'release_year': {'S': str(game['expected_release_year'])},
                    'platform': {'SS': [platform['name'] for platform in game['platforms']]},
                    'summary': {'S': game['deck']}
                }
            )
            print(response)
            return True
        return False
        
