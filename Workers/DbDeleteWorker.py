from .BaseWorker import BaseWorker

class DbDeleteWorker(BaseWorker):

    def __init__(self):
        super().__init__()

    def delete_item(self, key):
        response = {'status': 'FAIL'}
        try:
            db_response = self.dynamodb.delete_item(
                Key={
                    'guid': key
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