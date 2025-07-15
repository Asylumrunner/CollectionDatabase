from .BaseWorker import BaseWorker
import logging

class MediaItemWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_item_query = ("INSERT INTO items "
                     "(title, media_type, release_year, created_by, img_link, original_api_id) "
                     "VALUES (%s, %s, %s, %s, %s, %s)")
        
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
        
        self.get_item_query = ("SELECT title, mt.type_name, release_year, date_added, created_by, img_link, {} "
                               "FROM items i "
                               "JOIN {} sl ON i.id = sl.id"
                               "JOIN media_types mt ON mt.id = i.media_type "
                               "WHERE i.id = %s ")
        
        # Item Query Customizations are formatted into get_item_query to allow for specific joins based on the media type
        self.iqc_album = "summary"
        self.iqc_board_game = "maximum_players, minimum_players, summary, duration"
        self.iqc_book = "isbn, printing_year"
        self.iqc_movie = "lang, summary, duration"
        self.iqc_rpg = "isbn, summary"
        self.iqc_video_game = "summary"
        
        self.get_user_items_query = ("SELECT * FROM collection_items "
                    "INNER JOIN items ON collection_items.item_id = items.id AND collection_items.user_id = %s")

    def add_item(self, item):
        response = {'passed': False}
        cursor = self.database.cursor()
        try:
            cursor.execute(self.add_item_query, item['name'], self.media_type_mappings[item['media_type']], item['release_year'], item['created_by'], item['img_link'], item['original_api_id'])
            generated_id = cursor._last_insert_id
            match item['media_type']:
                case "book":
                    cursor.execute(self.add_book_query, generated_id, item['isbn'], item['printing_year'])
                case "movie":
                    cursor.execute(self.add_movie_query, generated_id, item['lang'], item['summary'], item['duration'])
                case "video_game":
                    cursor.execute(self.add_video_game_query, generated_id)
                    # Do more logic to add platforms
                case "board_game":
                    cursor.execute(self.add_board_game_query, generated_id)
                case "rpg":
                    cursor.execute(self.add_rpg_query, generated_id)
                case "anime":
                    cursor.execute(self.add_anime_query, generated_id)
                case "album":
                    cursor.execute(self.add_album_query, generated_id)
                case _:
                    raise ValueError("Media type unexpected. Aborting insertion")
            response['passed'] = True
        except Exception as e:
            logging.error("Exception while retrieving items from database: {}".format(e))
            response['exception'] = str(e)
            self.database.commit()
        finally:
            cursor.close()
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

    