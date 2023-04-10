from abc import ABC, abstractmethod
from fuzzywuzzy import process
import boto3
from .secrets import secrets

class GenreController(ABC):

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Table('CollectionTable')
        self.s3 = boto3.resource('s3', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Object(bucket_name='collectiontablebackup', key=self.guid_prefix + "Backup")

    def fuzzy_string_match(self, inputString, candidateStrings, threshold=50):
        best_candidate = process.extractOne(inputString, candidateStrings, score_cutoff=threshold)
        return best_candidate

    @abstractmethod
    def lookup_entry(self, title, picky):
        pass
    
    @abstractmethod
    def put_key(self, key):
        pass

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
    def back_up_table(self):
        pass
    
    @abstractmethod
    def restore_table(self):
        pass
"""
    @abstractmethod
    def wipe_table(self):
        pass
     """