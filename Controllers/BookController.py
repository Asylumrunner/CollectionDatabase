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