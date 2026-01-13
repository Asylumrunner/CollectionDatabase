from abc import ABC, abstractmethod
from Workers.secrets import secrets
from mysql.connector import pooling

class BaseWorker(ABC):
    database = None
    media_type_mappings = {}

    _connection_pool = pooling.MySQLConnectionPool(
        pool_name="pool",
        pool_size=5,
        pool_reset_session=True,
        host=secrets['database_endpoint'],
        database=secrets['collection_database_name'],
        user=secrets['database_username'],
        password=secrets['database_password']
    )

    def get_connection(self):
        return self._connection_pool.get_connection()

    def get_cursor(self, dictionary=False):
        connection = self.get_connection()
        return connection.cursor(dictionary=dictionary)

    def close_cursor_and_connection(self, cursor):
        if cursor:
            connection = cursor.connection
            cursor.close()
            if connection:
                connection.close()

