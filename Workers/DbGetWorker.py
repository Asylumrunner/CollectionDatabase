from .BaseWorker import BaseWorker
from boto3.dynamodb.conditions import Key, Attr
import logging

class DbGetWorker(BaseWorker):
    def __init__(self):
        super().__init__()

    def get_user_items(self, user_id):
        response = {'passed': False}
        try:
            query = "SELECT * FROM collection_items WHERE user_id = \'{}\'".format(user_id)
            cursor = self.database.cursor()
            cursor.execute(query)
            response['data'] = cursor.fetchall()
            cursor.close()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving items from database: {}".format(e))
            response['exception'] = str(e)
        return response
    
    def get_item(self, key):
        response = {'passed': False}
        try:
            db_response = self.dynamodb.get_item(
                Key={
                    'guid': key
                }
            )
            if('Item' in db_response):
                response['item'] = db_response['Item']
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving key {} from database: {}".format(key, e))
            response['exception'] = str(e)
        return response
    
    def get_table(self, included_types):
        response = {'items': [], 'passed': False}
        db_response = {}
        done_searching = False
        try:
            while not done_searching:
                if('LastEvaluatedKey' not in db_response): 
                    db_response = self.dynamodb.scan(
                        FilterExpression=Attr('media_type').is_in(included_types)
                    )
                else:
                    db_response = self.dynamodb.scan(
                        FilterExpression=Attr('media_type').is_in(included_types),
                        ExclusiveStartKey=db_response['LastEvaluatedKey']
                    )
                if(db_response['Items']):
                    response['items'].extend(db_response['Items'])
                done_searching = not db_response['Items'] or not 'LastEvaluatedKey' in db_response
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while getting table from database: {}".format(e))
            response['exception'] = str(e)
        return response      