import requests
from genre_controller import GenreController
import xml.etree.ElementTree as ET
import concurrent.futures

class BoardGameController(GenreController):
    def __init__(self):
        self.lookup_req_template = "https://www.boardgamegeek.com/xmlapi2/search?query={}&type=boardgame"
        self.individual_item_template = "https://www.boardgamegeek.com/xmlapi2/thing?id={}"
    
    def game_detail_lookup(self, child):
        item_dict = {}
        item_dict['guid'] = child.get('id', '00000')
        item_search_req = requests.get(self.individual_item_template.format(item_dict['guid']))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        names = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary']
        item_dict['name'] = names[0]
        item_dict['minimum_players'] = search_root.find('./minplayers').get('value', "-1")
        item_dict['maximum_players'] = search_root.find('./maxplayers').get('value', "a billion")
        item_dict['year_published'] = search_root.find('./yearpublished').get('value', '0')
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
            
        

