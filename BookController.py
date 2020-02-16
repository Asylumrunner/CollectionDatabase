import requests
from secrets import secrets
import xml.etree.ElementTree as ET
from genre_controller import GenreController

class BookController(GenreController):
    def __init__(self):
        self.GR_API_KEY = secrets['Goodreads_API_Key']
        self.lookup_req_template = "https://www.goodreads.com/search/index.xml?key={}&q={}&page={}"
        self.individual_item_template = "https://www.goodreads.com/book/show/{}.xml?key={}"
        self.guid_prefix = "BK-"
        super().__init__()

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.GR_API_KEY, title, 1))
        root = ET.fromstring(req.content)
        results = root.find('./search/results')
        response = [{'name': book.find('./best_book/title').text, 'author': book.find('./best_book/author/name').text, 'guid': book.find('./best_book/id').text, 'original_publication_date': book.find('./original_publication_year').text} for book in results]
        return response

    def put_key(self, key):
        print(self.individual_item_template.format(key, self.GR_API_KEY))
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
    
    def get_key(self, key):
        response = {'status': 'FAIL'}
        db_response = self.dynamodb.get_item(
            TableName='CollectionTable',
            Key={
                'guid': self.guid_prefix + key
            }
        )
        if(db_response['Item']):
            response['item'] = db_response['Item']
            response['status'] = 'OK'
        return response


