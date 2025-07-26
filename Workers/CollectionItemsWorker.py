from .BaseWorker import BaseWorker
import logging

class CollectionItemsWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_collection_item_query = ("INSERT INTO collection_items "
                                          "(item_id, user_id) "
                                          "SELECT %s, u.user_id "
                                          "FROM users u "
                                          "WHERE u.cognito_id = %s")
        
        self.delete_collection_item_query = ("DELETE FROM collection_items "
                                             "WHERE item_id = %s " 
                                             "AND user_id IN (SELECT user_id FROM users WHERE cognito_id = %s)")

        self.get_user_collection_query = ("SELECT items.id, title, media_types.type_name, release_year, date_added, date_last_updated, created_by, img_link "
                                          "FROM collection_items "
                                          "JOIN items ON collection_items.item_id = items.id "
                                          "JOIN media_types ON items.media_type = media_types.id "
                                          "JOIN users ON collection_items.user_id = users.user_id "
                                          "WHERE users.cognito_id = %s")
        

    def add_collection_item(self, item_id, cognito_id):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.add_collection_item_query, item_id, cognito_id)
            self.database.commit()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while adding collection item: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response
    
    def delete_collection_item(self, item_id, cognito_id):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.delete_collection_item_query, item_id, cognito_id)
            self.database.commit()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while removing collection item: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response
    
