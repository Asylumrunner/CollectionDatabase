from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json
import discogs_client
import pprint

class MusicController(GenreController):

    def __init__(self):
        self.guid_prefix = "CD-"
        self.discogs_client = discogs_client.Client('CollectionDatabase/0.1', user_token=secrets['Discogs_Developer_Token'])
        super().__init__()

    def lookup_entry(self, title, picky=False):

        pp = pprint.PrettyPrinter()
        results = self.discogs_client.search(title, type='release')
        response = []
        for release in results:
            response.append({
                'name': release.data['title'],
                'guid': release.data['id'],
                'genre': release.data['genre']
            })
            print("Added {} to response".format(release.data['title']))
        return response

    
    def put_key(self, key):
        pass
