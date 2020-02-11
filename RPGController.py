import requests
from genre_controller import GenreController
import xml.etree.ElementTree as ET
import concurrent.futures

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
    
    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(title))
        root = ET.fromstring(req.content)
        response = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            lookups = executor.map(self.game_detail_lookup, root)
        
        for lookup in lookups:
            response.append(lookup)
        
        return response
    
    def put_key(self, key):
        req = requests.get(self.individual_item_template.format(key))
        if(req.status_code == 200):
            search_root = ET.fromstring(req.content).find('./item')
            name = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary'][0]
            year_published = search_root.find('./yearpublished').get('value', '0')
            description = search_root.find('./description').text
            if(name != 'ERROR' and year_published != '0' and description):
                response = self.dynamodb.put_item(
                    TableName='CollectionTable',
                    Item={
                        'guid': {'S': self.guid_prefix + key},
                        'original_guid': {'S': key},
                        'name': {'S': name},
                        'release_year': {'S': year_published},
                        'summary': {'S': description}
                    }
                )
                print(response)
                return True
            else:
                return False
        return False
        
