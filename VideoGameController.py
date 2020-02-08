import requests
from secrets import secrets
from genre_controller import GenreController

class VideoGameController(GenreController):
    
    def __init__(self):
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.GB_API_KEY, title), headers=self.header)
        response = [{'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': [platform['name'] for platform in game['platforms']]} for game in req.json()['results']]
        return response
