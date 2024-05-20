from abc import ABC, abstractmethod
import boto3
from .secrets import secrets
from boto3.dynamodb.conditions import Key
import json

class BaseWorker(ABC):

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Table('CollectionTable')
