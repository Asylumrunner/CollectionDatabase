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
            print("Exception while retrieving key {} from database via RPGController: {}".format(key, e))
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
            print("Exception while deleting key {} from database via RPGController: {}".format(key, e))
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
            print("Exception while getting RPG table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def back_up_table(self):
        response = {'status': 'FAIL'}
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
            print("Exception while backing up RPG table from database: {}".format(e))
            response['error_message'] = str(e)
        return response

    def restore_table(self):
        response = {'status': 'FAIL', 'controller': 'VideoGame'}
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


    def restore_table(self):
        response = {'status': 'FAIL', 'controller': 'RPG'}
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

