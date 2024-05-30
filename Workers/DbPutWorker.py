from .BaseWorker import BaseWorker
import logging
from uuid import uuid4
from datetime import datetime

class DbPutWorker(BaseWorker):
    def __init__(self):
        super().__init__()
    
    def put_item(self, entry):
        id = str(uuid4())
        timestamp = datetime.today().isoformat()
        response = {'passed': False}
        try:
            response['database_response'] = self.dynamodb.put_item(
                Item={**entry, 'guid': id, "date_inserted": timestamp, "date_updated": timestamp}
            )
            response['passed'] = True
        except Exception as e:
            logging.error(f'Exception while inserting into database: {e}')
            response['exception'] = str(e)
        
        return response