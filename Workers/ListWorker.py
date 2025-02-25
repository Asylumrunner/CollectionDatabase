from .secrets import secrets
from .BaseWorker import BaseWorker

class ListWorker(BaseWorker):
    def __init__(self):
        super().__init__()

    def create_list(self, name, user):
        cursor = self.database.cursor()
        add_list = ("INSERT INTO lists "
                    "(name, owner_id) "
                    "VALUES (%s, %s)")
        cursor.execute(add_list, (name, user))
        self.database.commit()
        cursor.close()

    def get_all_lists(self, user):
        cursor = self.database.cursor()
        query = ("SELECT id, name FROM lists "
                 "WHERE owner_id = %s ")
        cursor.execute(query, (user))
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
        query = ("SELECT name, type, release_year, img_link "
                 "FROM items i "
                 "JOIN list_items li on i.id = li.item_id "
                 "JOIN lists l on li.list_id = l.id"
                 "WHERE li.list_id = %s AND l.owner_id = %s ")
        cursor.execute(query, (listId, user))
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
        delete_list = ("DELETE FROM lists "
                    "WHERE id = %s and owner_id = %s")
        cursor.execute(delete_list, (listId, user))
        self.database.commit()
        cursor.close()
        return True
    
    def add_item_to_list(self, listId, item, user):
        cursor = self.database.cursor()
        return None
    
    def delete_item_from_list(self, listId, item, user):
        # TODO: Create endpoint
        return None
