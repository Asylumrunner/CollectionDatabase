from .BaseWorker import BaseWorker
import logging
from uuid import uuid5

class DbPutWorker(BaseWorker):
    def __init__(self):
        super().__init__()
    
    def put_item(self, entry):
        id = uuid5()
        response = {'status': 'FAIL'}
        try:
            response['database_response'] = self.dynamodb.put_item(
                Item={**entry, 'guid': id}
            )
            response['status'] = 'SUCCESS'
        except Exception as e:
            logging.error(f'Exception while inserting into database: {e}')
            response['exception'] = e
        
        return response