from abc import ABC, abstractmethod
import boto3
from secrets import secrets

class GenreController(ABC):

    def __init__(self):
        self.dynamodb = boto3.client('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY'],)

    @abstractmethod
    def lookup_entry(self, title, **kwargs):
        pass
    
    @abstractmethod
    def put_key(self, key):
        pass
"""
    @abstractmethod
    def get_key(self, key):
        pass

    @abstractmethod
    def delete_key(self, key):
        pass

    @abstractmethod
    def get_table(self):
        pass

    @abstractmethod
    def wipe_table(self):
        pass
     """