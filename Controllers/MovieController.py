import requests
import concurrent.futures
from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json

class MovieController(GenreController):
    def __init__(self):
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.lookup_req_template = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true"
        self.movie_lookup_template = "https://api.themoviedb.org/3/movie/{}?api_key={}"
        self.guid_prefix = "MV-"
        super().__init__()

    def movie_lookup(self, guid):
        movie = requests.get(self.movie_lookup_template.format(guid, self.MDB_API_KEY)).json()
        response = {'name': movie['title'], 'guid': movie['id'], 'release_year': movie['release_date'][:4], 'language': movie['original_language'], 'summary': movie['overview'], 'runtime': movie['runtime']}
        return response

    def lookup_entry(self, title, picky=False):
        response = []
        try:
            req = requests.get(self.lookup_req_template.format(self.MDB_API_KEY, title))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])
            
            for lookup in lookups:
                response.append(lookup)
            
            if picky:
                best_movie = self.fuzzy_string_match(title, [movie['name'] for movie in response])
                response = [movie for movie in response if movie['name'] == best_movie[0]]
        except Exception as e:
            print("Exception in lookup for title {} in MovieController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def put_key(self, key):
        try:
            req = requests.get(self.movie_lookup_template.format(key, self.MDB_API_KEY))
            if(req.status_code == 200):
                movie = req.json()
                response = self.dynamodb.put_item(
                    Item={
                        'guid': self.guid_prefix + str(movie['id']),
                        'original_guid': str(movie['id']),
                        'name': movie['title'],
                        'release_year': movie['release_date'][:4],
                        'language': movie['original_language'],
                        'summary': movie['overview'],
                        'duration': str(movie['runtime'])
                    }
                )
                print(response)
                return True
            return False
        except Exception as e:
            print("Exception while putting key {} in database via MovieController: {}".format(key, e))
            return False