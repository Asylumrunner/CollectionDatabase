import requests
from .genre_controller import GenreController
import xml.etree.ElementTree as ET
import concurrent.futures
from boto3.dynamodb.conditions import Key
import json

class RPGController(GenreController):
    def __init__(self):
        self.lookup_req_template = "https://www.rpggeek.com/xmlapi2/search?query={}&type=rpgitem"
        self.individual_item_template = "https://www.rpggeek.com/xmlapi2/thing?id={}"
        self.guid_prefix = "RP-"
        super().__init__()

    def game_detail_lookup(self, child):
        item_dict = {}
        item_dict['guid'] = child.get('id', '00000')
        item_search_req = requests.get(self.individual_item_template.format(item_dict['guid']))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        names = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary']
        item_dict['name'] = names[0]
        item_dict['release_year'] = search_root.find('./yearpublished').get('value', '0')
        item_dict['summary'] = search_root.find('./description').text
        return item_dict
    
    def lookup_entry(self, title, picky=False):
        response = []
        try:
            req = requests.get(self.lookup_req_template.format(title))
            root = ET.fromstring(req.content)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.game_detail_lookup, root)
            
            for lookup in lookups:
                response.append(lookup)
            
            if picky:
                best_game = self.fuzzy_string_match(title, [game['name'] for game in response])
                response = [game for game in response if game['name'] == best_game[0]]
        except Exception as e:
            print("Exception in lookup for title {} in RPGController: {}".format(title, e))
            response = [{
                'Exception': str(e)
            }]
        return response
    
    def put_key(self, key):
        try:
            req = requests.get(self.individual_item_template.format(key))
            if(req.status_code == 200):
                search_root = ET.fromstring(req.content).find('./item')
                name = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary'][0]
                year_published = search_root.find('./yearpublished').get('value', '0')
                description = search_root.find('./description').text
                if(name != 'ERROR' and year_published != '0' and description):
                    response = self.dynamodb.put_item(
                        Item={
                            'guid': self.guid_prefix + key,
                            'original_guid': key,
                            'name': name,
                            'release_year': year_published,
                            'summary': description
                        }
                    )
                    print(response)
                    return True
                else:
                    return False
            return False
        except Exception as e:
            print("Exception while putting key {} in database via RPGController: {}".format(key, e))
            return False

