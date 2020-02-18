import requests
from secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json

class VideoGameController(GenreController):
    
    def __init__(self):
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"
        self.game_key_req_template = "https://www.giantbomb.com/api/game/{}/?api_key={}&format=json"
        self.guid_prefix = "VG-"
        super().__init__()

    def lookup_entry(self, title, **kwargs):
        try:
            req = requests.get(self.lookup_req_template.format(self.GB_API_KEY, title), headers=self.header)
            response = [{'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': [platform['name'] for platform in game['platforms']]} for game in req.json()['results']]
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
    
    def get_key(self, key):
        response = {'status': 'FAIL'}
        try:
            db_response = self.dynamodb.get_item(
                Key={
                    'guid': self.guid_prefix + key
                }
            )
            if(db_response['Item']):
                response['item'] = db_response['Item']
                response['item']['platform'] = list(response['item']['platform'])
                response['status'] = 'OK'
        except Exception as e:
            print("Exception while retrieving key {} from database via VideoGameController: {}".format(key, e))
            response['error_message'] = str(e)
        return response
    
    def delete_key(self, key):
        response = {'status': 'FAIL'}
        try:
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
        except Exception as e:
            print("Exception while deleting key {} from database via VideoGameController: {}".format(key, e))
            response['error_message'] = str(e)
        return response

    def get_table(self):
        response = {}
        db_response = {}
        try:
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
        except Exception as e:
            print("Exception while getting video game table from database: {}".format(e))
            response['error_message'] = str(e)
        return response
    
    def back_up_table(self):
        response = {'status': 'FAIL', 'controller': 'VideoGame'}
        try:
            table_contents = self.get_table()
            if('error_message' not in table_contents and 'Items' in table_contents):
                guids = {'guids': [item['guid'] for item in table_contents['Items']]}
                s3_response = self.s3.put_object(Key=self.guid_prefix + "Backup", Body=bytes(json.dumps(guids).encode('UTF-8')))
                response['object'] = s3_response
                response['status'] = 'OK'
            elif('error_message' in table_contents):
                response['error_message'] = table_contents['error_message']
            else:
                response['error_message'] = "No table items to back up"
        except Exception as e:
            print("Exception while backing up video game table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

