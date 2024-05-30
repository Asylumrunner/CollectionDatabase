from .secrets import secrets
from .BaseWorker import BaseWorker
from jikanpy import Jikan
import xml.etree.ElementTree as ET
import concurrent.futures
import discogs_client
import logging
import requests
import pprint

class SearchWorker(BaseWorker):
    def __init__(self):
        # Used for Anime Lookup
        self.jikan_client = Jikan()

        # Used for Board Game Lookup
        self.bg_lookup_req_template = "https://www.boardgamegeek.com/xmlapi2/search?query={}&type=boardgame"
        self.bg_individual_item_template = "https://www.boardgamegeek.com/xmlapi2/thing?id={}"

        # Used for Book Lookup
        self.book_lookup_req_template = "https://openlibrary.org/search.json?q={}&page={}"

        # Used for Movie Lookup
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.movie_lookup_req_template = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true"
        self.movie_lookup_template = "https://api.themoviedb.org/3/movie/{}?api_key={}"
        self.movie_credits_lookup_template = "https://api.themoviedb.org/3/movie/{}/credits?api_key={}"

        # Used for Music Lookup
        self.discogs_client = discogs_client.Client('CollectionDatabase/0.1', user_token=secrets['Discogs_Developer_Token'])

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
        elif media_type == "board_game":
            return self.lookup_board_game(name)
        elif media_type == "rpg":
            return self.lookup_rpg(name)
        elif media_type == "anime":
            return self.lookup_anime(name)
        elif media_type == "music":
            return self.lookup_music(name)
        else:
            logging.error("media_type passed to LookupWorker not recognized")
            return [{
                "Exception": f'media_type {media_type} not recognized. Please use one of [book, movie, video_game, board_game, rpg, anime, music]'
            }]
        
    def lookup_book(self, title):
        try:
            formatted_title = title.replace(' ', '+')
            page_num = 1
            openLibResponse = requests.get(self.book_lookup_req_template.format(formatted_title, page_num)).json()
            response = []
            
            for book in openLibResponse["docs"]:
                response.append([{'name': book['title'], 'release_year': book['first_publish_year'], 'img_link': "https://covers.openlibrary.org/b/isbn/{}-L.jpg".format(book['isbn'][0]), 'guid': book['key'], 'created_by': ", ".join(book["author_name"])}])            
        except Exception as e:
            print("Exception in lookup for title {} in BookController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def movie_lookup(self, guid):
        movie = requests.get(self.movie_lookup_template.format(guid, self.MDB_API_KEY)).json()
        credits = requests.get(self.movie_credits_lookup_template.format(guid, self.MDB_API_KEY)).json()
        directors = ", ".join([crewmember['name'] for crewmember in credits['crew'] if crewmember['job'] == 'Director'])
        response = {'name': movie['title'], 'guid': movie['id'], 'release_year': movie['release_date'][:4], 'created_by': directors, 'img_link': "https://image.tmdb.org/t/p/w600_and_h900_bestv2{}".format(movie['poster_path']), 'language': movie['original_language'], 'summary': movie['overview'], 'duration': movie['runtime']}
        return response
    
    def lookup_movie(self, title):
        response = []
        try:
            req = requests.get(self.movie_lookup_req_template.format(self.MDB_API_KEY, title))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])
            
            for lookup in lookups:
                response.append(lookup)
            
        except Exception as e:
            print("Exception in lookup for title {} in MovieController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response

    def lookup_video_game(self, title):
        try:
            req = requests.get(self.vg_lookup_req_template.format(self.GB_API_KEY, title), headers=self.header).json()
            response = []
            for game in req['results']:
                platforms = [platform['name'] for platform in game['platforms']] if game['platforms'] else ""
                response.append({'name': game['name'], 'summary': game['deck'], 'release_year': game['expected_release_year'], 'guid': game['guid'], 'platforms': platforms})
        except Exception as e:
            print("Exception in lookup for title {} in VideoGameController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response
    
    def lookup_board_game(self, title):
        response = []
        try:
            req = requests.get(self.bg_lookup_req_template.format(title))
            root = ET.fromstring(req.content)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.board_game_detail_lookup, root)
            
            for lookup in lookups:
                response.append(lookup)
            
        except Exception as e:
            print("Exception in lookup for title {} in BoardGameController: {}".format(title, e))
            response = [{
                "Exception": str(e)
            }]
        return response

    def board_game_detail_lookup(self, child):
        item_dict = {}
        item_dict['guid'] = child.get('id', '00000')
        item_search_req = requests.get(self.bg_individual_item_template.format(item_dict['guid']))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        names = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary']
        item_dict['name'] = names[0]
        item_dict['minimum_players'] = search_root.find('./minplayers').get('value', "-1")
        item_dict['maximum_players'] = search_root.find('./maxplayers').get('value', "a billion")
        item_dict['year_published'] = search_root.find('./yearpublished').get('value', '0')
        item_dict['summary'] = search_root.find('./description').text
        item_dict['duration'] = search_root.find('./playingtime').get('value', 'eternity')
        return item_dict
    
    def lookup_rpg(self, title):
        response = []
        try:
            req = requests.get(self.rpg_lookup_req_template.format(title))
            root = ET.fromstring(req.content)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.rpg_detail_lookup, root)
            
            for lookup in lookups:
                response.append(lookup)

        except Exception as e:
            print("Exception in lookup for title {} in RPGController: {}".format(title, e))
            response = [{
                'Exception': str(e)
            }]
        return response

    def rpg_detail_lookup(self, child):
        item_dict = {}
        item_dict['guid'] = child.get('id', '00000')
        item_search_req = requests.get(self.rpg_individual_item_template.format(item_dict['guid']))
        search_root = ET.fromstring(item_search_req.content).find('./item')
        names = [name.get('value', 'ERROR') for name in search_root.iterfind('name') if name.get('type', 'alternate') == 'primary']
        item_dict['name'] = names[0]
        item_dict['release_year'] = search_root.find('./yearpublished').get('value', '0')
        item_dict['summary'] = search_root.find('./description').text
        return item_dict
    
    def lookup_anime(self, title):
        jikan_response = self.jikan_client.search("anime", title)
        response = []
        for anime in jikan_response['data']:
            response.append({
                'name': anime['title_english'],
                'guid': anime['mal_id'],
                'release_year': anime['aired']['prop']['from']['year'],
                'summary': anime['synopsis'],
                'episodes': anime['episodes']
            })
        return response
    
    def lookup_music(self, title):
        results = self.discogs_client.search(title, type='release', release_title=title)
        response = []
        for release in results.page(0):
            response.append({
                'name': release.data['title'],
                'guid': release.data['id'],
                'genre': release.data['genre']
            })
        return response