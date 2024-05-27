from .BaseWorker import BaseWorker
import logging

class DbUpdateWorker(BaseWorker):

    def __init__(self):
        super().__init__()
    
    def update_entry(self, guid, updated_fields):
        response = {'status': 'FAIL'}
        updateExpression = "set"
        expressionAttributeValues = {}
        for field_name, new_value in updated_fields:
            updateString = f' {field_name} = :{field_name[0]}'
            updateExpression += updateString
            expressionAttributeValues[f':{field_name[0]}'] = new_value
        try:
            response['database_response'] = self.dynamodb.update_item(
                Key={
                    'guid': guid
                },
                UpdateExpression=updateExpression,
                ExpressionAttributeValues=expressionAttributeValues,
                ReturnValues="ALL_NEW"
            )
            response['status'] = 'SUCCESS'
        except Exception as e:
            logging.error(f'Exception while updating database item at key {guid}: {e}')
            response['exception'] = e
        return response
