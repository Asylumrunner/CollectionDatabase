from abc import ABC, abstractmethod
from Workers.secrets import secrets

class BaseWorker(ABC):
    database = None
    media_type_mappings = {}
