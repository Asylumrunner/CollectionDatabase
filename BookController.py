import requests
from secrets import secrets
import xml.etree.ElementTree as ET
from genre_controller import GenreController

class BookController(GenreController):
    def __init__(self):
        self.GR_API_KEY = secrets['Goodreads_API_Key']
        self.lookup_req_template = "https://www.goodreads.com/search/index.xml?key={}&q={}&page={}"
    
    def lookup_entry(self, title, **kwargs):
        req = requests.get(self.lookup_req_template.format(self.GR_API_KEY, title, 1))
        root = ET.fromstring(req.content)
        results = root.find('./search/results')
        response = [{'name': book.find('./best_book/title').text, 'author': book.find('./best_book/author/name').text, 'guid': book.find('./id').text, 'original_publication_date': book.find('./original_publication_year').text} for book in results]
        return response