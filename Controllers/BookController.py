import requests
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
from Collections.SeattlePublicLibrary import SeattlePublicLibrary
import json

class BookController(GenreController):
    def __init__(self):
        self.lookup_req_template = "https://openlibrary.org/isbn/{}.json"
        self.lookup_author_template = "https://openlibrary.org{}.json"
        self.guid_prefix = "BK-"
        self.library = SeattlePublicLibrary()
        super().__init__()

    def lookup_entry(self, title, picky=False):
        try:
            ISBN = title
            book = requests.get(self.lookup_req_template.format(ISBN)).json()

            authors = []
            for author in book['authors']:
                try:
                    author_req = requests.get(self.lookup_author_template.format(author['key'])).json()
                    authors.append(author_req['name'])
                except Exception as e:
                    print("Exception in author lookup for {} in BookController: {}".format(author, e))
            if len(authors) != len(book['authors']):
                raise ValueError("Length of authors retrieved {} does not match expected length {}".format(len(authors), len(book['authors'])))

            response = [{'name': book['title'], 'guid': book['key'][7:], 'authors': ", ".join(authors), 'release_year': book['publish_date'][len(book['publish_date'])-4:], 'isbn': book['isbn_13'][0], 'page_count': book['number_of_pages']}]
        except Exception as e:
            print("Exception in lookup for ISBN {} in BookController: {}".format(ISBN, e))
            response = [{
                "Exception": str(e)
            }]
        return response

    def put_key(self, key):
        try:
            req = self.lookup_entry(key)
            if 'Exception' not in req:
                response = self.dynamodb.put_item(
                    Item={
                        'guid': self.guid_prefix + req['guid'],
                        'original_guid': req['guid'],
                        'name': req['name'],
                        'authors': req['authors'],
                        'release_year': req['release_year'],
                        'isbn': key
                    }
                )
                return True
            return False
        except Exception as e:
            print("Exception while putting key {} in database via BookController: {}".format(key, e))
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
            print("Exception while retrieving key {} from database via BookController: {}".format(key, e))
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
            print("Exception while deleting key {} from database via BookController: {}".format(key, e))
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
            print("Exception while getting book table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def back_up_table(self):
        response = {'status': 'FAIL', 'controller': 'Book'}
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
            print("Exception while backing up book table from database: {}".format(e))
            response['error_message'] = str(e)
        return response
    
    def library_compare(self, key):
        response = {'status': 'FAIL', 'match': False}
        lookup_response = self.get_key(key)
        if(lookup_response['status'] == 'OK'):
            response['DB_Item'] = lookup_response['item']
            isbn = lookup_response['item']['isbn']
            library_lookup_response = self.library.search_collection_by_isbn(isbn)
            if(library_lookup_response['status'] == 'OK' and library_lookup_response['library_response']):
                response['match'] = True
                response['Library_Item'] = self.consolidate_library_results(library_lookup_response['library_response'])
                response['status'] = 'OK'
            elif(library_lookup_response['status'] == 'FAIL'):
                response['error_message'] = library_lookup_response['error_message']
            else:
                response['status'] = 'OK'
        return response

    def restore_table(self):
        response = {'status': 'FAIL', 'controller': 'Book'}
        try:
            s3_response = self.s3.get()
            s3_response_body = json.loads(s3_response['Body'].read().decode("utf-8"))
            for guid in s3_response_body['guids']:
                self.put_key(guid)
            response['object'] = s3_response_body
            response['status'] = 'OK'
        except Exception as e:
            print('Exception while restoring book table from database: {}'.format(e))
            print['error_message'] = str(e)
        return response

    def consolidate_library_results(self, raw_library_response):
        consolidated_lib_res = []
        for item in raw_library_response:
            matches = [found_item for found_item in consolidated_lib_res if found_item['bibnum'] == item['bibnum']]
            if matches:
                matches[0]['itemcount'] = str(int(matches[0]['itemcount']) + 1)
                if item['itemlocation'] not in matches[0]['itemlocation']:
                    matches[0]['itemlocation'] += (", " + item['itemlocation'])
            else:
                consolidated_lib_res.append(item)
        return consolidated_lib_res