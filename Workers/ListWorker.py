from .secrets import secrets
from .BaseWorker import BaseWorker

class ListWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_list_query = ("INSERT INTO lists "
                    "(name, owner_id) "
                    "VALUES (%s, %s)")
        
        self.get_lists_query = ("SELECT id, name FROM lists "
                 "WHERE owner_id = %s ")
        
        # I feel like this is fucked but lemme double check
        self.get_list_query = ("SELECT name, type, release_year, img_link "
                 "FROM items i "
                 "JOIN list_items li on i.id = li.item_id "
                 "JOIN lists l on li.list_id = l.id"
                 "WHERE li.list_id = %s AND l.owner_id = %s ")
        
        self.add_item_to_list_query ("INSERT INTO list_items "
                                     "(item_id, list_id) "
                                     "VALUES (%s %s)" )
        
        self.delete_list_query = ("DELETE FROM lists "
                    "WHERE id = %s and owner_id = %s")
        
        self.delete_list_item_query = ("DELETE FROM list_items "
                    "WHERE id = %s and owner_id = %s")

    def create_list(self, name, user):
        cursor = self.database.cursor()
        cursor.execute(self.add_list_query, (name, user))
        self.database.commit()
        cursor.close()

    def get_all_lists(self, user):
        cursor = self.database.cursor()
        cursor.execute(self.get_lists_query, (user))
        results = []
        for (id, name) in cursor:
            results.append({
                id,
                name
            })
        cursor.close()
        return results
    
    def get_list(self, listId, user):
        cursor = self.database.cursor()
        cursor.execute(self.get_list_query, (listId, user))
        results = []
        for (name, type, release_year, img_link) in cursor:
            results.append({
                name,
                type,
                release_year,
                img_link
            })
        cursor.close()
        return results

    def delete_list(self, listId, user):
        cursor = self.database.cursor()
        cursor.execute(self.delete_list_query, (listId, user))
        self.database.commit()
        cursor.close()
        return True
    
    def add_item_to_list(self, listId, item, user):
        cursor = self.database.cursor()
        return None
    
    def delete_item_from_list(self, listId, item, user):
        cursor = self.database.cursor()
        return None
