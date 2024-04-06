import requests
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
from Collections.SeattlePublicLibrary import SeattlePublicLibrary
import json

class BookController(GenreController):
    def __init__(self):
        self.lookup_req_template = "https://openlibrary.org/search.json?q={}&page={}"
        self.guid_prefix = "BK-"
        self.library = SeattlePublicLibrary()
        super().__init__()

    def lookup_entry(self, title, picky=False):
        try:
            formatted_title = title.replace(' ', '+')
            page_num = 1
            openLibResponse = requests.get(self.lookup_req_template.format(formatted_title, page_num)).json()
            response = []
            
            for book in openLibResponse["docs"]:
                response.append([{'name': book['title'], 'guid': book['key'], 'authors': ", ".join(book["author_name"])}])            
        except Exception as e:
            print("Exception in lookup for title {} in BookController: {}".format(title, e))
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
                        'authors': req['authors']
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