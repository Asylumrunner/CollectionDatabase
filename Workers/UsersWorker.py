from .BaseWorker import BaseWorker
import logging

class UsersWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_user_query = ("INSERT INTO users "
                               "(cognito_id, username) "
                               "VALUES (%s, %s)")
        
        self.get_user_query = ("SELECT username FROM users" 
                               "WHERE users.cognito_id = %s")
        
        self.delete_user_query = ("DELETE FROM users "
                                  "WHERE cognito_id = %s")
        
        self.delete_user_collection_items_query = ("DELETE FROM collection_items ci"
                                              "JOIN users u ON u.user_id = ci.user_id "
                                              "WHERE u.cognito_id = %s")
        
        self.delete_user_list_items_query = ("DELETE FROM list_items "
                                            "WHERE list_id IN (SELECT list_id FROM user_lists ul JOIN users u ON u.user_id = ul.user_id WHERE u.cognito_id = %s)")
        
        self.delete_user_lists_query = ("DELETE FROM user_lists ul "
                                        "JOIN users u on u.user_id = ul.user_id "
                                        "WHERE u.cognito_id = %s")
        
        self.change_username_query = ("UPDATE users "
                                      "SET username = %s "
                                      "WHERE cognito_id = %s")

    def add_user(self, cognito_id, username):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.add_user_query, cognito_id, username)
            self.database.commit()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while adding user: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response
    
    def get_user(self, cognito_id):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.get_user_query, cognito_id)
            user_data = cursor.fetchall()
            if not user_data:
                raise KeyError("User not found")
            response['data'] = user_data
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving user: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response

    def delete_user(self, cognito_id):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.delete_user_list_items_query, cognito_id)
            cursor.execute(self.delete_user_lists_query, cognito_id)
            cursor.execute(self.delete_user_collection_items_query, cognito_id)
            cursor.execute(self.delete_user_query, cognito_id)
            self.database.commit()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while deleting user: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response
    
    def change_username(self, cognito_id, new_username):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.change_username_query, cognito_id, new_username)
            self.database.commit()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while updating username: {}".format(e))
            response['exception'] = str(e)
            self.database.rollback()
        finally:
            cursor.close()
        return response
