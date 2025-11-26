import pprint
from .secrets import secrets
from .BaseWorker import BaseWorker
from DataClasses.item import Item
from jikanpy import Jikan
import xml.etree.ElementTree as ET
import concurrent.futures
import logging
import requests
from benedict import benedict

class SearchWorker(BaseWorker):
    def __init__(self):
        # Used for Anime Lookup
        self.jikan_client = Jikan()

        # Used for Board Game Lookup
        self.bg_lookup_req_template = "https://www.boardgamegeek.com/xmlapi2/search?query={}&type=boardgame"
        self.bg_individual_item_template = "https://www.boardgamegeek.com/xmlapi2/thing?id={}"

        # Used for Book Lookup
        self.book_lookup_req_template = "https://openlibrary.org/search.json?q={}&page={}&fields=key,title,author_name,cover_i,first_publish_year,editions,editions.isbn,editions.publish_date"

        # Used for Movie Lookup
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.movie_lookup_req_template = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true"
        self.movie_lookup_template = "https://api.themoviedb.org/3/movie/{}?api_key={}"
        self.movie_credits_lookup_template = "https://api.themoviedb.org/3/movie/{}/credits?api_key={}"

        # Used for Music Lookup
        self.AUDIODB_API_KEY = secrets['AudioDB_Key']
        self.music_lookup_req_template = "https://www.theaudiodb.com/api/v1/json/{}/searchalbum.php?s={}"

        # Used for RPG Lookup
        self.rpg_lookup_req_template = "https://www.rpggeek.com/xmlapi2/search?query={}&type=rpgitem"
        self.rpg_individual_item_template = "https://www.rpggeek.com/xmlapi2/thing?id={}"

        # Used for Video Game Lookup
        self.GB_API_KEY = secrets['Giant_Bomb_API_Key']
        self.header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        self.vg_lookup_req_template = "http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game"
        self.game_key_req_template = "https://www.giantbomb.com/api/game/{}/?api_key={}&format=json"

        super().__init__()

    def search_item(self, name, media_type):
        if media_type == "book":
            return self.lookup_book(name)
        elif media_type == "movie":
            return self.lookup_movie(name)
        elif media_type == "video_game":
            return self.lookup_video_game(name)
        # elif media_type == "board_game":
        #     return self.lookup_board_game(name)
        # elif media_type == "rpg":
        #     return self.lookup_rpg(name)
        elif media_type == "anime":
            return self.lookup_anime(name)
        elif media_type == "music":
            return self.lookup_music(name)
        else:
            logging.error("media_type passed to LookupWorker not recognized")
            return {
                "passed": False,
                "exception": f'media_type {media_type} not recognized. Please use one of [book, movie, video_game, board_game, rpg, anime, music]'
            }
        
    def lookup_book(self, title):
        try:
            formatted_title = title.replace(' ', '+')
            page_num = 1
            openLibResponse = requests.get(self.book_lookup_req_template.format(formatted_title, page_num)).json()
            response = {"items": [], "passed": False}
            
            for book in openLibResponse["docs"]:
                title = getIfUseful(book, 'title')
                release_year = getIfUseful(book, 'first_publish_year')
                isbn = book['editions']['docs'][0]['isbn'][0] if 'isbn' in book['editions']['docs'][0] else ''
                img_link = "https://covers.openlibrary.org/a/id/{}-M.jpg".format(book['cover_i']) if 'cover_i' in book else ''
                created_by = getIfUseful(book, "author_name")
                media_type = "book"
                item = Item(
                    book['key'], title, media_type, release_year, img_link, book['key'], created_by, isbn, release_year
                )
                response["items"].append(item)
            response["passed"] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in BookController: {}".format(title, e))
            response["exception"] = str(e)
        return response
    
    def movie_lookup(self, guid):
        movie = requests.get(self.movie_lookup_template.format(guid, self.MDB_API_KEY)).json()
        movie_id = movie.get('id', '')
        
        credits = requests.get(self.movie_credits_lookup_template.format(guid, self.MDB_API_KEY)).json()
        crew = getIfUseful(credits, 'crew', [])
        directors = []
        for crewmember in crew:
            if crewmember.get('job') == 'Director':
                directors.append(crewmember.get('name', 'Unknown Director'))
        
        title = getIfUseful( movie, 'title')
        release_year = movie.get('release_date', '0000')[:4]
        img_link = "https://image.tmdb.org/t/p/w600_and_h900_bestv2{}".format(movie['poster_path']) if 'poster_path' in movie else None
        language = getIfUseful(movie, 'original_language')
        summary = getIfUseful(movie, 'overview')
        duration = getIfUseful(movie, 'runtime')
        media_type = "movie"
        item = Item(
            movie_id, title, media_type, release_year, img_link, movie_id, directors, language=language, summary=summary, duration=duration
        )

        return item
    
    def lookup_movie(self, title):
        response = {"items": [], "passed": False}
        try:
            req = requests.get(self.movie_lookup_req_template.format(self.MDB_API_KEY, title))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])
            
            for lookup in lookups:
                response['items'].append(lookup)
            
            response["passed"] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in MovieController: {}".format(title, e))
            response["exception"] = str(e)
        return response

    def lookup_video_game(self, title):
        response = {"items": [], "passed": False}
        try:
            req = requests.get(self.vg_lookup_req_template.format(self.GB_API_KEY, title), headers=self.header).json()
            for game in req['results']:
                game_details = benedict(requests.get(self.game_key_req_template.format(game['guid'], self.GB_API_KEY), headers=self.header).json())
                developer = game_details['results.developers[0].name'] if 'results.developers[0].name' in game_details else ""
                platform_objs = getIfUseful(game, 'platforms', [])
                platforms = [getIfUseful(platform, 'name') for platform in platform_objs]
                game_title = getIfUseful(game, 'name')
                img_link = getIfUseful(game, 'image', {}).get('medium_url')
                summary = getIfUseful(game, 'deck')
                release_year = getIfUseful(game, 'original_release_date', '')[:4]
                media_type = "video_game"
                guid = game['guid']
                item = Item(
                    guid, game_title, media_type, release_year, img_link, guid, developer, summary=summary, platforms=platforms
                )
                response['items'].append(item)
            response["passed"] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in VideoGameController: {}".format(title, e))
            response["exception"] = str(e)
        return response
    
    def lookup_board_game(self, title):
        response = {"items": [], "passed": False}
        try:
            req = requests.get(self.bg_lookup_req_template.format(title))
            root = ET.fromstring(req.content)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.board_game_detail_lookup, root)
            
            for lookup in lookups:
                if lookup:
                    response['items'].append(lookup)
            
            response["passed"] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in BoardGameController: {}".format(title, e))
            response["exception"] = str(e)
        return response

    def board_game_detail_lookup(self, child):
        item_dict = {}
        guid = child.get('id', '00000')
        item_search_req = requests.get(self.bg_individual_item_template.format(guid))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        if search_root:
            names = [name.get('value') for name in search_root.iterfind('name') if name.get('type') == 'primary']
            item_dict['title'] = names[0]
            item_dict['img_link'] = search_root.find('./image').text if search_root.find('./image') is not None else None
            designers = [designer.get('value', 'unknown') for designer in search_root.iterfind('link') if designer.get('type') == 'boardgamedesigner']
            item_dict['created_by'] = designers
            item_dict['original_api_id'] = guid
            item_dict['minimum_players'] = search_root.find('./minplayers').get('value')
            item_dict['maximum_players'] = search_root.find('./maxplayers').get('value')
            item_dict['year_published'] = search_root.find('./yearpublished').get('value')
            item_dict['summary'] = search_root.find('./description').text
            item_dict['total_duration'] = search_root.find('./playingtime').get('value')
            item_dict['media_type'] = "board_game"
            return item_dict
        else:
            return {}
    
    def lookup_rpg(self, title):
        response = {"items": [], "passed": False}
        try:
            req = requests.get(self.rpg_lookup_req_template.format(title))
            root = ET.fromstring(req.content)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.rpg_detail_lookup, root)
            
            for lookup in lookups:
                if lookup:
                    response["items"].append(lookup)
            
            response['passed'] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in RPGController: {}".format(title, e))
            response["exception"] = str(e)
        return response

    def rpg_detail_lookup(self, child):
        item_dict = {}
        guid = child.get('id', '00000')
        item_search_req = requests.get(self.rpg_individual_item_template.format(guid))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        if search_root:
            names = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary']
            item_dict['title'] = names[0]
            item_dict['img_link'] = search_root.find('./image').text if search_root.find('./image') is not None else None
            designers = [designer.get('value') for designer in search_root.iterfind('link') if designer.get('type', 'none') == 'rpgdesigner']
            item_dict['created_by'] = designers
            item_dict['release_year'] = search_root.find('./yearpublished').get('value', '0')
            item_dict['original_api_id'] = guid
            item_dict['summary'] = search_root.find('./description').text
            item_dict['media_type'] = "rpg"
            return item_dict
        else:
            return {}
    
    def lookup_anime(self, title):
        response = {"items": [], "passed": False}
        try:
            jikan_response = self.jikan_client.search("anime", title)
            for anime in jikan_response['data']:
                item = Item(
                    anime['mal_id'], anime.get('title_english'), "anime", anime['aired']['prop']['from']['year'], anime['images']['jpg']['image_url'], anime['mal_id'], [studio['name'] for studio in anime['studios']], summary=anime.get('synopsis'), episodes=anime['episodes']
                )
                response['items'].append(item)
            response['passed'] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in AnimeController: {}".format(title, e))
            response["exception"] = str(e)
        return response
    
    def lookup_music(self, artist):
        response = {"items": [], "passed": False}
        try:
            results = requests.get(self.music_lookup_req_template.format(self.AUDIODB_API_KEY, artist)).json()
            for release in results['album']:
                response['items'].append({
                    'title': release.get('strAlbumStripped'),
                    'img_link': release.get('strAlbumThumb'),
                    'release_year': release.get('intYearReleased'),
                    'created_by': release.get('strArtistStripped'),
                    'original_api_id': release['idAlbum'],
                    'summary': release.get('strDescriptionEN'),
                    'media_type': 'music'
                })
            response['passed'] = True
        except Exception as e:
            logging.error("Exception in lookup for title {} in MusicController: {}".format(artist, e))
            response["exception"] = str(e)
        return response

# Utility function to save some readability
# Returns value for key if it exists and is truthy, otherwise returns default value
def getIfUseful(object, key, defaultValue=None):
    if isinstance(key, list):
        search_ptr = object
        for subkey in key:
            search_ptr = search_ptr.get(subkey, None)
            if not bool(search_ptr):
                return defaultValue
        return search_ptr
    else:
        value = object.get(key, None)
        return value if bool(value) else defaultValue