import requests
import concurrent.futures
from secrets import secrets
from genre_controller import GenreController

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

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.MDB_API_KEY, title))
        response = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])
        
        for lookup in lookups:
            response.append(lookup)
        
        return response
    
    def put_key(self, key):
        req = requests.get(self.movie_lookup_template.format(key, self.MDB_API_KEY))
        if(req.status_code == 200):
            movie = req.json()
            response = self.dynamodb.put_item(
                TableName='CollectionTable',
                Item={
                    'guid': {'S': self.guid_prefix + str(movie['id'])},
                    'original_guid': {'S': str(movie['id'])},
                    'name': {'S': movie['title']},
                    'release_year': {'S': movie['release_date'][:4]},
                    'language': {'S': movie['original_language']},
                    'summary': {'S': movie['overview']},
                    'duration': {'S': str(movie['runtime'])}
                }
            )
            print(response)
            return True
        return False

