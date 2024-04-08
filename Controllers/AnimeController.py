from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
from jikanpy import Jikan


class AnimeController(GenreController):

    def __init__(self):
        self.guid_prefix = "AN-"
        self.jikan_client = Jikan()
        super().__init__()

    def lookup_entry(self, title, picky=False):
        jikan_response = self.jikan_client.search("anime", title)
        response = []
        for anime in jikan_response['data']:
            response.append({
                'name': anime['title_english'],
                'guid': anime['mal_id'],
                'release_year': anime['aired']['prop']['from']['year'],
                'summary': anime['synopsis'],
                'episodes': anime['episodes']
            })
        return response

    
    def put_key(self, key):
        req = self.jikan_client.anime(key)['data']
        print(req)
        if (req):
            response = self.dynamodb.put_item(
                Item={
                    'name': req['title_english'],
                    'guid': self.guid_prefix + str(req['mal_id']),
                    'release_year': str(req['year']),
                    'summary': req['synopsis'],
                    'episodes': str(req['episodes'])
                }
            )
            print(response)
            return True
        return False