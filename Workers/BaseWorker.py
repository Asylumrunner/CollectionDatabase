from contextlib import contextmanager
import contextlib
from Workers.secrets import secrets
from mysql.connector import pooling, Error
from mysql.connector.errors import PoolError
import json
import logging
import os
import sys
import time

# Set up logging
logger = logging.getLogger(__name__)

_LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'local_db_config.json')

_POOL_SIZE = 5
# Thresholds above which connection activity is logged as a warning
_SLOW_ACQUIRE_MS = 100
_LONG_HOLD_MS = 1000

def _find_caller():
    # Walk up past this module and contextlib to find the worker method that asked for a connection
    frame = sys._getframe(1)
    while frame and frame.f_code.co_filename in (__file__, contextlib.__file__):
        frame = frame.f_back
    if not frame:
        return "unknown"
    return f"{os.path.basename(frame.f_code.co_filename)}:{frame.f_code.co_name}:{frame.f_lineno}"

class BaseWorker():
    media_type_mappings = {}
    _connection_pool = None
    _pool_initialized = False

    @classmethod
    def _initialize_pool(cls):
        if cls._pool_initialized:
            return

        start = time.perf_counter()
        try:
            if os.path.exists(_LOCAL_CONFIG_PATH):
                with open(_LOCAL_CONFIG_PATH) as f:
                    local_config = json.load(f)
                db_host = local_config['host']
                db_port = int(local_config.get('port', 3306))
                db_name = local_config['database']
                db_user = local_config['username']
                db_password = local_config['password']
                logger.info("Using local database config")
            else:
                db_host = secrets['database_endpoint']
                db_port = 3306
                db_name = secrets['collection_database_name']
                db_user = secrets['database_username']
                db_password = secrets['database_password']

            cls._connection_pool = pooling.MySQLConnectionPool(
                pool_name="collection_pool",
                pool_size=_POOL_SIZE,
                pool_reset_session=True,
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            cls._pool_initialized = True
            logger.info(f"Database connection pool initialized successfully: host={db_host} port={db_port} database={db_name} pool_size={_POOL_SIZE} init_ms={(time.perf_counter() - start) * 1000:.0f}")
            cls._load_media_type_mappings()
        except Error as e:
            logger.error(f"Failed to initialize connection pool after {(time.perf_counter() - start) * 1000:.0f}ms: {e}")
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

        start = time.perf_counter()
        try:
            return self._connection_pool.get_connection()
        except PoolError as e:
            # mysql-connector's pool doesn't wait for a free connection, it fails immediately
            logger.error(f"Connection pool exhausted: caller={_find_caller()} pool_size={_POOL_SIZE}: {e}")
            raise
        except Error as e:
            logger.error(f"Failed to get connection from pool after {(time.perf_counter() - start) * 1000:.0f}ms: {e}")
            raise

    @contextmanager
    def _checked_out_connection(self):
        # Warns when a connection is slow to acquire or held for a long time
        acquire_start = time.perf_counter()
        connection = self.get_connection()
        acquired_at = time.perf_counter()
        acquire_ms = (acquired_at - acquire_start) * 1000
        if acquire_ms > _SLOW_ACQUIRE_MS:
            logger.warning(f"Slow connection acquire: id={connection.connection_id} caller={_find_caller()} acquire_ms={acquire_ms:.0f}")

        try:
            yield connection
        finally:
            held_ms = (time.perf_counter() - acquired_at) * 1000
            if held_ms > _LONG_HOLD_MS:
                logger.warning(f"Connection held a long time: id={connection.connection_id} caller={_find_caller()} held_ms={held_ms:.0f}")
            connection.close()  # Returns to pool

    @contextmanager
    def get_connection_context(self):
        try:
            with self._checked_out_connection() as connection:
                yield connection
        except Error as e:
            logger.error(f"Database error in connection context: {e}")
            raise

    @contextmanager
    def get_cursor_context(self, dictionary=False):
        try:
            with self._checked_out_connection() as connection:
                cursor = connection.cursor(dictionary=dictionary)
                try:
                    yield cursor
                finally:
                    cursor.close()
        except Error as e:
            logger.error(f"Database error in cursor context: {e}")
            raise

