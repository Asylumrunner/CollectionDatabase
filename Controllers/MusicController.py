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
        results = self.discogs_client.search(title, type='release', release_title=title)
        response = []
        for release in results.page(0):
            pprint.pp(release)
            response.append({
                'name': release.data['title'],
                'guid': release.data['id'],
                'genre': release.data['genre']
            })
        return response

    
    def put_key(self, key):
        req = self.discogs_client.release(key)
        if (req):
            response = self.dynamodb.put_item(
                Item={
                    'name': req.title,
                    'guid': self.guid_prefix + str(req.id),
                    'genre': req.genres
                }
            )
            print(response)
            return True
        return False
