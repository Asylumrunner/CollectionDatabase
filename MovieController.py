import requests
from secrets import secrets
from genre_controller import GenreController

class MovieController(GenreController):
    def __init__(self):
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.lookup_req_template = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true"

    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.MDB_API_KEY, title))
        response = [{'name': movie['title'], 'guid': movie['id'], 'original_release_year': movie['release_date'][:4], 'language': movie['original_language']} for movie in req.json()['results']]
        return response