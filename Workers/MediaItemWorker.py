from .BaseWorker import BaseWorker
import logging

class MediaItemWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_item_query = ("INSERT INTO items "
                     "(title, media_type, release_year, created_by, img_link, original_api_id) "
                     "SELECT m.id, %s, %s, %s, %s, %s "
                     "FROM media_types m "
                     "WHERE m.type_name = %s")
        self.add_album_query = ("INSERT INTO albums "
                                "(id, summary) "
                                "VALUES (%s, %s)")
        self.add_anime_query = ("INSERT INTO anime "
                                "(id, episodes, summary) "
                                "VALUES (%s, %s, %s)")
        self.add_board_game_query = ("INSERT INTO board_games "
                                      "(id, minimum_players, maximum_players, summary, duration) "
                                      "VALUES (%s, %s, %s, %s, %s)")
        self.add_book_query = ("INSERT INTO books "
                               "(id, isbn, printing_year) "
                               "VALUES (%s, %s, %s)")
        self.add_movie_query = ("INSERT INTO movies "
                                "(id, lang, summary, duration) "
                                "VALUES (%s, %s, %s, %s)")
        self.add_rpg_query = ("INSERT INTO rpgs "
                              "(id, isbn, summary) "
                              "VALUES (%s, %s, %s)")
        self.add_video_game_query = ("INSERT INTO video_games "
                                     "(id, summary) "
                                     "VALUES (%s, %s)")
        self.add_video_game_availability_query = ("INSERT INTO game_platform_availabilities "
                                                  "(game_id, platform_id) "
                                                  "SELECT %s, p.platform_id "
                                                  "FROM video_game_platforms p "
                                                  "WHERE p.platform_name = %s")
        
        self.get_item_query = ("SELECT title, mt.type_name, release_year, date_added, created_by, img_link, {}"
                               "FROM items i "
                               "JOIN {} sl ON i.id = sl.id"
                               "JOIN media_types mt ON mt.id = i.media_type "
                               "WHERE i.id = %s ")
        
        self.get_user_items_query = ("SELECT * FROM collection_items "
                    "INNER JOIN items ON collection_items.item_id = items.id AND collection_items.user_id = %s")

    def add_item(self, user, item):
        response = {'passed': False}
        try:
            
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving items from database: {}".format(e))
            response['exception'] = str(e)
        return response

    def get_user_items(self, user_id):
        response = {'passed': False}
        try:
            cursor = self.database.cursor()
            cursor.execute(self.get_user_items_query, user_id)
            response['data'] = cursor.fetchall()
            cursor.close()
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving items from database: {}".format(e))
            response['exception'] = str(e)
        return response

    