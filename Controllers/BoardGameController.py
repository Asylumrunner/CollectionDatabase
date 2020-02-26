import requests
from .genre_controller import GenreController
import xml.etree.ElementTree as ET
import concurrent.futures
from boto3.dynamodb.conditions import Key
import json

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
            print("Exception while retrieving key {} from database via BoardGameController: {}".format(key, e))
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
            print("Exception while deleting key {} from database via BoardGameController: {}".format(key, e))
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
            print("Exception while getting board game table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def back_up_table(self):
        response = {'status': 'FAIL', 'controller': 'BoardGame'}
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
            print("Exception while backing up board game table from database: {}".format(e))
            response['error_message'] = str(e)
        return response
    
    def restore_table(self):
        response = {'status': 'FAIL', 'controller': 'BoardGame'}
        try:
            s3_response = self.s3.get()
            s3_response_body = json.loads(s3_response['Body'].read().decode("utf-8"))
            for guid in s3_response_body['guids']:
                self.put_key(guid)
            response['object'] = s3_response_body
            response['status'] = 'OK'
        except Exception as e:
            print('Exception while restoring video game table from database: {}'.format(e))
            print['error_message'] = str(e)
        return response
