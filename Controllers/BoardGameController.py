import requests
from .genre_controller import GenreController
import xml.etree.ElementTree as ET
import concurrent.futures
from boto3.dynamodb.conditions import Key
import pprint

class BoardGameController(GenreController):
    def __init__(self):
        self.lookup_req_template = "https://www.boardgamegeek.com/xmlapi2/search?query={}&type=boardgame"
        self.individual_item_template = "https://www.boardgamegeek.com/xmlapi2/thing?id={}"
        self.guid_prefix='BG-'
        super().__init__()

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
        item_dict['summary'] = search_root.find('./description').text
        item_dict['duration'] = search_root.find('./playingtime').get('value', 'eternity')
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
            print("Exception in lookup for title {} in BoardGameController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def put_key(self, key):
        try:
            req = requests.get(self.individual_item_template.format(key))
            if(req.status_code == 200):
                search_root = ET.fromstring(req.content).find('./item')
                name = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary'][0]
                year_published = search_root.find('./yearpublished').get('value', '0')
                summary = search_root.find('./description').text
                minimum_players = search_root.find('./minplayers').get('value', "-1")
                maximum_players = search_root.find('./maxplayers').get('value', "a billion")
                duration = search_root.find('./playingtime').get('value', 'eternity')
                if(name != 'ERROR' and year_published != 0 and summary and minimum_players != "-1" and maximum_players != "a billion" and duration != "eternity"):
                    response = self.dynamodb.put_item(
                        Item={
                            'guid': self.guid_prefix + key,
                            'original_guid': key,
                            'name': name,
                            'release_year': year_published,
                            'summary': summary,
                            'minimum_players': minimum_players,
                            'maximum_players': maximum_players,
                            'duration': duration
                        }
                    )
                    print(response)
                    return True
                else:
                    return False
            return False
        except Exception as e:
            print("Exception while putting key {} in database via BoardGameController: {}".format(key, e))
            return False
