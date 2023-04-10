import requests
from .secrets import secrets
from .genre_controller import GenreController
from boto3.dynamodb.conditions import Key
import json

class AnimeController(GenreController):

    def __init__(self):
        self.guid_prefix = "AN-"
        super().__init__()

    def lookup_entry(self, title, picky):
        pass
    
    def put_key(self, key):
        pass

    def get_key(self, key):
        pass

    def delete_key(self, key):
        pass

    def get_table(self):
        pass

    def back_up_table(self):
        pass
    
    def restore_table(self):
        pass
    
