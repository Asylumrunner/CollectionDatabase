import requests
from secrets import secrets
import xml.etree.ElementTree as ET
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
from Collections.SeattlePublicLibrary import SeattlePublicLibrary
import json

class BookController(GenreController):
    def __init__(self):
        self.GR_API_KEY = secrets['Goodreads_API_Key']
        self.lookup_req_template = "https://www.goodreads.com/search/index.xml?key={}&q={}&page={}"
        self.individual_item_template = "https://www.goodreads.com/book/show/{}.xml?key={}"
        self.guid_prefix = "BK-"
        self.library = SeattlePublicLibrary()
        super().__init__()

    def lookup_entry(self, title, **kwargs):
        try:
            req = requests.get(self.lookup_req_template.format(self.GR_API_KEY, title, 1))
            root = ET.fromstring(req.content)
            results = root.find('./search/results')
            response = [{'name': book.find('./best_book/title').text, 'author': book.find('./best_book/author/name').text, 'guid': book.find('./best_book/id').text, 'original_publication_date': book.find('./original_publication_year').text} for book in results]
        except Exception as e:
            print("Exception in lookup for title {} in BookController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response

    def put_key(self, key):
        try:
            req = requests.get(self.individual_item_template.format(key, self.GR_API_KEY))
            if(req.status_code == 200):
                root = ET.fromstring(req.content)
                result = root.find('./book')
                work = result.find('./work')
                name = result.find('./title').text
                author = result.find('./authors/author/name').text
                guid = result.find('./id').text
                year_published = work.find('./original_publication_year').text
                isbn = result.find('./isbn13').text
                description = result.find('./description').text

                response = self.dynamodb.put_item(
                    Item={
                        'guid': self.guid_prefix + guid,
                        'original_guid': guid,
                        'name': name,
                        'author': author,
                        'release_year': year_published,
                        'isbn': isbn,
                        'summary': description
                    }
                )
                print(response)
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
                s3_response = self.s3.put_object(Key=self.guid_prefix + "Backup", Body=bytes(json.dumps(guids).encode('UTF-8')))
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
                response['Library_Item'] = library_lookup_response['library_response']
                response['status'] = 'OK'
            elif(library_lookup_response['status'] == 'FAIL'):
                response['error_message'] = library_lookup_response['error_message']
            else:
                response['status'] = 'OK'
        return response