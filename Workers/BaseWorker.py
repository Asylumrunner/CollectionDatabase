from abc import ABC, abstractmethod
from contextlib import contextmanager
from Workers.secrets import secrets
from mysql.connector import pooling, Error
import logging

# Set up logging
logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    database = None
    media_type_mappings = {}
    _connection_pool = None
    _pool_initialized = False

    @classmethod
    def _initialize_pool(cls):
        if cls._pool_initialized:
            return

        try:
            cls._connection_pool = pooling.MySQLConnectionPool(
                pool_name="collection_pool",
                pool_size=5,
                pool_reset_session=True,
                host=secrets['database_endpoint'],
                database=secrets['collection_database_name'],
                user=secrets['database_username'],
                password=secrets['database_password']
            )
            cls._pool_initialized = True
            logger.info("Database connection pool initialized successfully")
            cls._load_media_type_mappings()
        except Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    @classmethod
    def _load_media_type_mappings(cls):
        connection = None
        cursor = None
        try:
            connection = cls._connection_pool.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, type_name FROM media_types")
            for row in cursor.fetchall():
                cls.media_type_mappings[row['type_name']] = row['id']
            logger.info(f"Loaded media type mappings: {cls.media_type_mappings}")
        except Error as e:
            logger.error(f"Failed to load media type mappings: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def get_connection(self):
        if not self._pool_initialized:
            self._initialize_pool()

        try:
            return self._connection_pool.get_connection()
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    @contextmanager
    def get_connection_context(self):
        connection = None
        try:
            connection = self.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Database error in connection context: {e}")
            raise
        finally:
            if connection:
                connection.close()  # Returns to pool

    @contextmanager
    def get_cursor_context(self, dictionary=False):
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=dictionary)
            yield cursor
        except Error as e:
            logger.error(f"Database error in cursor context: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()  # Returns to pool

