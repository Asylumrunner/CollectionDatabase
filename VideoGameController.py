import requests
from secrets import secrets
from genre_controller import GenreController
from boto3.dynamodb.conditions import Key

class VideoGameController(GenreController):
    
    def __init__(self):
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"
        self.game_key_req_template = "https://www.giantbomb.com/api/game/{}/?api_key={}&format=json"
        self.guid_prefix = "VG-"
        super().__init__()

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.GB_API_KEY, title), headers=self.header)
        response = [{'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': [platform['name'] for platform in game['platforms']]} for game in req.json()['results']]
        return response
    
    def put_key(self, key):
        req = requests.get(self.game_key_req_template.format(key, self.GB_API_KEY), headers=self.header)
        if(req.status_code == 200 and req.json()['error'] == 'OK'):
            game = req.json()['results']
            response = self.dynamodb.put_item(
                Item={
                    'guid': self.guid_prefix + game['guid'],
                    'original_guid': game['guid'],
                    'name': game['name'],
                    'release_year': str(game['expected_release_year']),
                    'platform': [platform['name'] for platform in game['platforms']],
                    'summary': game['deck']
                }
            )
            print(response)
            return True
        return False
    
    def get_key(self, key):
        response = {'status': 'FAIL'}
        db_response = self.dynamodb.get_item(
            Key={
                'guid': self.guid_prefix + key
            }
        )
        if(db_response['Item']):
            response['item'] = db_response['Item']
            response['item']['platform'] = list(response['item']['platform'])
            response['status'] = 'OK'
        return response
    
    def delete_key(self, key):
        response = {'status': 'FAIL'}
        db_response = self.dynamodb.delete_item(
            Key={
                'guid': self.guid_prefix + key
            },
            ReturnValues='ALL_OLD'
        )
        if(db_response['Attributes']):
            response['item'] = db_response['Attributes']
            response['item']['platform'] = list(response['item']['platform'])
            response['status'] = 'OK'
        return response

    def get_table(self):
        response = {}
        db_response = {}
        while not response or 'LastEvaluatedKey' in db_response:
            if('LastEvaluatedKey' not in db_response): 
                db_response = self.dynamodb.scan(
                    FilterExpression=Key('guid').begins_with(self.guid_prefix)
                )
            else:
                db_response = self.dynamodb.scan(
                    FilterExpression=Key('guid').begins_with(self.guid_prefix),
                    ExclusiveStartKey=db_response['LastEvaluatedKey']
                )
            if(db_response['Items']):
                response['Items'] = db_response['Items']
        for item in response['Items']: 
                item['platform'] = list(item['platform'])
        return response

