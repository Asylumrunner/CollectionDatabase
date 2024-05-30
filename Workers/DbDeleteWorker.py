from .BaseWorker import BaseWorker
import logging

class DbDeleteWorker(BaseWorker):

    def __init__(self):
        super().__init__()

    def delete_item(self, key):
        response = {'passed': False}
        try:
            db_response = self.dynamodb.delete_item(
                Key={
                    'guid': key
                },
                ReturnValues='ALL_OLD'
            )
            if('Attributes' in db_response):
                response['item'] = db_response['Attributes']
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while deleting key {} from database: {}".format(key, e))
            response['exception'] = str(e)
        return response