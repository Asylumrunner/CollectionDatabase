import requests
import concurrent.futures
from secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json

class MovieController(GenreController):
    def __init__(self):
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.lookup_req_template = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true"
        self.movie_lookup_template = "https://api.themoviedb.org/3/movie/{}?api_key={}"
        self.guid_prefix = "MV-"
        super().__init__()

    def movie_lookup(self, guid):
        movie = requests.get(self.movie_lookup_template.format(guid, self.MDB_API_KEY)).json()
        response = {'name': movie['title'], 'guid': movie['id'], 'release_year': movie['release_date'][:4], 'language': movie['original_language'], 'summary': movie['overview'], 'runtime': movie['runtime']}
        return response

    def lookup_entry(self, title, **kwargs):
        response = []
        try:
            req = requests.get(self.lookup_req_template.format(self.MDB_API_KEY, title))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])
            
            for lookup in lookups:
                response.append(lookup)
        except Exception as e:
            print("Exception in lookup for title {} in MovieController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def put_key(self, key):
        try:
            req = requests.get(self.movie_lookup_template.format(key, self.MDB_API_KEY))
            if(req.status_code == 200):
                movie = req.json()
                response = self.dynamodb.put_item(
                    Item={
                        'guid': self.guid_prefix + str(movie['id']),
                        'original_guid': str(movie['id']),
                        'name': movie['title'],
                        'release_year': movie['release_date'][:4],
                        'language': movie['original_language'],
                        'summary': movie['overview'],
                        'duration': str(movie['runtime'])
                    }
                )
                print(response)
                return True
            return False
        except Exception as e:
            print("Exception while putting key {} in database via MovieController: {}".format(key, e))
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
        response = {'status': 'FAIL', 'controller': 'Movie'}
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
        response = {'status': 'FAIL', 'controller': 'VideoGame'}
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
