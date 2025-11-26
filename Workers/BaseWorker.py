from abc import ABC, abstractmethod
from .secrets import secrets

class BaseWorker(ABC):
    database = None
    media_type_mappings = {}
