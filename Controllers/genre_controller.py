from abc import ABC, abstractmethod
from fuzzywuzzy import process
import boto3
from .secrets import secrets
from boto3.dynamodb.conditions import Key
import json

class GenreController(ABC):

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Table('CollectionTable')
        self.s3 = boto3.resource('s3', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Object(bucket_name='collectiontablebackup', key=self.guid_prefix + "Backup")

    def fuzzy_string_match(self, inputString, candidateStrings, threshold=50):
        best_candidate = process.extractOne(inputString, candidateStrings, score_cutoff=threshold)
        return best_candidate

    @abstractmethod
    def lookup_entry(self, title, picky):
        pass
    
    @abstractmethod
    def put_key(self, key):
        pass

    def get_key(self, key):
        response = {'status': 'FAIL'}
        try:
            db_response = self.dynamodb.get_item(
                Key={
                    'guid': self.guid_prefix + key
                }
            )
            if('Item' in db_response):
                response['item'] = db_response['Item']
            response['status'] = 'OK'
        except Exception as e:
            print("Exception while retrieving key {} from database: {}".format(key, e))
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
            if('Attributes' in db_response):
                response['item'] = db_response['Attributes']
            response['status'] = 'OK'
        except Exception as e:
            print("Exception while deleting key {} from database: {}".format(key, e))
            response['error_message'] = str(e)
        return response

    def get_table(self):
        response = {}
        try:
            db_response = self.dynamodb.scan(
                            FilterExpression=Key('guid').begins_with(self.guid_prefix)
                        )          
            if('Items' in db_response):
                response['Items'] = db_response['Items']
        
            while 'LastEvaluatedKey' in db_response:
                db_response = self.dynamodb.scan(
                    FilterExpression=Key('guid').begins_with(self.guid_prefix),
                    ExclusiveStartKey=db_response['LastEvaluatedKey']
                )
                response['Items'] + db_response['Items']
        except Exception as e:
            print("Exception while getting table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def back_up_table(self):
        response = {'status': 'FAIL', 'controller': type(self).__name__}
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
            print("Exception while backing up table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def restore_table(self):
        response = {'status': 'FAIL', 'controller': type(self).__name__}
        try:
            s3_response = self.s3.get()
            s3_response_body = json.loads(s3_response['Body'].read().decode("utf-8"))
            for guid in s3_response_body['guids']:
                self.put_key(guid)
            response['object'] = s3_response_body
            response['status'] = 'OK'
        except Exception as e:
            print('Exception while restoring table from database: {}'.format(e))
            print['error_message'] = str(e)
        return response


"""
    @abstractmethod
    def wipe_table(self):
        pass
     """