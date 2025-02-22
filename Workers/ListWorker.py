from .secrets import secrets
from .BaseWorker import BaseWorker

class ListWorker(BaseWorker):
    def __init__(self):
        super().__init__()

    def create_list(self, name):
        # TODO: Create endpoint
        return None

    def get_list(self, listId):
        # TODO: Create endpoint
        return None

    def delete_list(self, listId):
        # TODO: Create endpoint
        return None
    
    def add_item_to_list(self, listId, item):
        # TODO: Create endpoint
        return None
    
    def delete_item_from_list(self, listId, item):
        # TODO: Create endpoint
        return None
