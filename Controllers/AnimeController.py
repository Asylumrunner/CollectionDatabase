from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
from jikanpy import Jikan
import json

class AnimeController(GenreController):

    def __init__(self):
        self.guid_prefix = "AN-"
        self.jikan_client = Jikan()
        super().__init__()

    def lookup_entry(self, title, picky=False):
        jikan_response = self.jikan_client.search("anime", title)
        response = []
        for anime in jikan_response['data']:
            response.append({
                'name': anime['title_english'],
                'guid': anime['mal_id'],
                'release_year': anime['year'],
                'summary': anime['synopsis'],
                'episodes': anime['episodes']
            })
        return response

    
    def put_key(self, key):
        req = self.jikan_client.anime(key)['data']
        print(req)
        if (req):
            response = self.dynamodb.put_item(
                Item={
                    'name': req['title_english'],
                    'guid': self.guid_prefix + str(req['mal_id']),
                    'release_year': str(req['year']),
                    'summary': req['synopsis'],
                    'episodes': str(req['episodes'])
                }
            )
            print(response)
            return True
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
                response['status'] = 'OK'
        except Exception as e:
            print("Exception while retrieving key {} from database via MovieController: {}".format(key, e))
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
                response['status'] = 'OK'
        except Exception as e:
            print("Exception while deleting key {} from database via MovieController: {}".format(key, e))
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
        except Exception as e:
            print("Exception while getting movie table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def back_up_table(self):
        response = {'status': 'FAIL', 'controller': 'Anime'}
        try:
            table_contents = self.get_table()
            if('error_message' not in table_contents and 'Items' in table_contents):
                guids = {'guids': [item['original_guid'] for item in table_contents['Items']]}
                s3_response = self.s3.put(Body=bytes(json.dumps(guids).encode('UTF-8')))
                response['object'] = s3_response
                response['status'] = 'OK'
            elif('error_message' in table_contents):
                response['error_message'] = table_contents['error_message']
            else:
                response['error_message'] = "No table items to back up"
        except Exception as e:
            print("Exception while backing up movie table from database: {}".format(e))
            response['error_message'] = str(e)
        return response
    
    def restore_table(self):
        response = {'status': 'FAIL', 'controller': 'Anime'}
        try:
            s3_response = self.s3.get()
            s3_response_body = json.loads(s3_response['Body'].read().decode("utf-8"))
            for guid in s3_response_body['guids']:
                self.put_key(guid)
            response['object'] = s3_response_body
            response['status'] = 'OK'
        except Exception as e:
            print('Exception while restoring video game table from database: {}'.format(e))
            print['error_message'] = str(e)
        return response
    
