from abc import ABC, abstractmethod
import boto3
from .secrets import secrets
from boto3.dynamodb.conditions import Key
import mysql.connector

class BaseWorker(ABC):
    database = None
    media_type_mappings = {}

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=secrets['ACCESS_KEY'], aws_secret_access_key=secrets['SECRET_KEY']).Table('CollectionTable')
        if BaseWorker.database is None:
            BaseWorker.database = mysql.connector.connect(host=secrets["database_endpoint"], user=secrets["database_username"], password=secrets["database_password"], database=secrets["collection_database_name"], port=3306)
        if not BaseWorker.media_type_mappings:
            cursor = BaseWorker.database.cursor()
            cursor.execute("SELECT id, type_name FROM media_types")
            for row in cursor.fetchall():
                BaseWorker.media_type_mappings[row[0]] = row[1]
                BaseWorker.media_type_mappings[row[1]] = row[0]
            cursor.close()
        else:
            print(BaseWorker.media_type_mappings)
