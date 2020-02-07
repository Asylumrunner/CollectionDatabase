from abc import ABC, abstractmethod

class GenreController(ABC):
    @abstractmethod
    def lookup_entry(self, title, **kwargs):
        pass

"""     @abstractmethod
    def post_key(self, key):
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
    def wipe_table(self):
        pass
     """