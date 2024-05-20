from .BaseWorker import BaseWorker
from boto3.dynamodb.conditions import Key


class DbGetWorker(BaseWorker):
    def __init__(self):
        super().__init__()
    
    def get_item(self, key):
        response = {'status': 'FAIL'}
        try:
            db_response = self.dynamodb.get_item(
                Key={
                    'guid': key
                }
            )
            if('Item' in db_response):
                response['item'] = db_response['Item']
            response['status'] = 'OK'
        except Exception as e:
            print("Exception while retrieving key {} from database: {}".format(key, e))
            response['error_message'] = str(e)
        return response
    
    def get_table(self, key, included_types):
        response = {'Items': []}
        db_response = {}
        done_searching = False
        try:
            while not done_searching:
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
                    response['Items'].extend(db_response['Items'])
                done_searching = not db_response['Items'] or not 'LastEvaluatedKey' in db_response
        except Exception as e:
            print("Exception while getting table from database: {}".format(e))
            response['error_message'] = str(e)
        return response      