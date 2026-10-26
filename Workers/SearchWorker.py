import pprint
from Workers.secrets import secrets
from Workers.BaseWorker import BaseWorker
from DataClasses.item import Item
from DataClasses.igdb_platforms import get_platform_id
from jikanpy import Jikan
import discogs_client
import xml.etree.ElementTree as ET
import concurrent.futures
import logging
import requests
from benedict import benedict
from datetime import datetime
import traceback
import sys
import time

class SearchWorker(BaseWorker):
    def __init__(self):
        # Used for Anime Lookup
        self.jikan_client = Jikan()

        # Used for Board Game Lookup
        self.bgg_base_url = "https://boardgamegeek.com/xmlapi2"
        self.bgg_header = {'Authorization': f"Bearer {secrets['BGG_API_Key']}"}

        # Used for Book Lookup
        self.book_lookup_url = "https://openlibrary.org/search.json"
        self.book_lookup_fields = "key,title,author_name,cover_i,first_publish_year,editions,editions.isbn,editions.publish_date"

        # Used for Movie Lookup
        self.MDB_API_KEY = secrets['MovieDB_Key']
        self.tmdb_base_url = "https://api.themoviedb.org/3"

        # Used for Music Lookup - Discogs API
        self.DISCOGS_USER_TOKEN = secrets['Discogs_Token']
        self.discogs_client = discogs_client.Client(
            'CollectionDatabase/1.0',
            user_token=self.DISCOGS_USER_TOKEN
        )

        # Used for RPG Lookup
        self.rpggeek_base_url = "https://rpggeek.com/xmlapi2"

        # Used for Video Game Lookup
        self.IGDB_Client_ID = secrets['IGDB_Client_ID']
        self.IGDB_Client_Secret = secrets['IGDB_Client_Secret']
        self.vg_lookup_url = "https://api.igdb.com/v4/games"
        self.vg_lookup_fields = "artworks,cover.image_id,created_at,first_release_date,involved_companies.company.name,language_supports,name,platforms.name,ports,status,summary"
        try:
            logging.info("Fetching IGDB access token...")
            self.get_IGDB_Access_Token()
            logging.info("IGDB access token fetched successfully.")
        except Exception as e:
            logging.error(f"Failed to fetch IGDB access token during SearchWorker init: {e}", exc_info=True)
            raise

        super().__init__()

    def get_IGDB_Access_Token(self):
        access_token_response = requests.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": self.IGDB_Client_ID,
            "client_secret": self.IGDB_Client_Secret,
            "grant_type": "client_credentials",
        }).json()
        self.IGDB_Access_Token = access_token_response['access_token']
        self.IGDB_Token_Last_Set = datetime.now()
        self.IGDB_Time_Until_Token_Refresh = access_token_response['expires_in']

        self.IGDB_headers = {
            "Client-ID": self.IGDB_Client_ID,
            "Authorization": f"Bearer {self.IGDB_Access_Token}",
        }

    def _build_exception_dict(self, exception, context_info):
        _exc_type, _exc_value, exc_traceback = sys.exc_info()

        return {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "traceback": traceback.format_exc(),
            "traceback_lines": traceback.format_tb(exc_traceback),
            "context": context_info,
            "exception_args": exception.args if hasattr(exception, 'args') else None
        }

    def search_item(self, name, media_type, pagination_key=None, search_options=None):
        pagination_key = pagination_key if pagination_key else 1
        search_options = search_options if search_options else {}
        lookups = {
            "book": self.lookup_book,
            "movie": self.lookup_movie,
            "video_game": self.lookup_video_game,
            "board_game": self.lookup_board_game,
            "rpg": self.lookup_rpg,
            "anime": self.lookup_anime,
            "album": self.lookup_music,
        }
        if media_type not in lookups:
            logging.error("media_type passed to LookupWorker not recognized")
            return {
                "passed": False,
                "exception": f'media_type {media_type} not recognized. Please use one of [book, movie, video_game, board_game, rpg, anime, album]'
            }

        logging.info(f"Search started: media_type={media_type} query={name!r} page={pagination_key} search_options={search_options}")
        start = time.perf_counter()
        response = None
        try:
            response = lookups[media_type](name, pagination_key, search_options)
            return response
        finally:
            self._log_search_result(name, media_type, pagination_key, search_options, response, time.perf_counter() - start)

    def _log_search_result(self, name, media_type, pagination_key, search_options, response, elapsed):
        summary = f"media_type={media_type} query={name!r} page={pagination_key} search_options={search_options} duration_ms={elapsed * 1000:.0f}"
        if response is None:
            # Lookup raised instead of returning a response dict
            logging.error(f"Search crashed: {summary}")
        elif response.get("passed"):
            logging.info(f"Search succeeded: {summary} item_count={len(response.get('items', []))} next_page={response.get('next_page')}")
        else:
            exception = response.get("exception")
            error_type = exception.get("error_type") if isinstance(exception, dict) else None
            error_message = exception.get("error_message") if isinstance(exception, dict) else exception
            logging.warning(f"Search failed: {summary} error_type={error_type} error_message={error_message!r}")
        
    def lookup_book(self, title, pagination_key, search_options={}):
        response = {"items": [], "passed": False}
        try:
            # Build the search query - all filters go into the 'q' parameter
            query_parts = [title]

            # Add direct search filters to query
            recognized_params = [
                'author', 'subject', 'place', 'person', 'language',
                'publisher', 'edition_count', 'author_key'
            ]

            for param in recognized_params:
                if param in search_options:
                    query_parts.append(f"{param}:{search_options[param]}")

            # Handle range parameters that need special formatting
            # publish_year: [earliest_publish_year TO latest_publish_year]
            if 'earliest_publish_year' in search_options or 'latest_publish_year' in search_options:
                earliest = search_options.get('earliest_publish_year', '*')
                latest = search_options.get('latest_publish_year', '*')
                query_parts.append(f"publish_year:[{earliest} TO {latest}]")

            # first_publish_year: [earliest_first_publish_year TO latest_first_publish_year]
            if 'earliest_first_publish_year' in search_options or 'latest_first_publish_year' in search_options:
                earliest = search_options.get('earliest_first_publish_year', '*')
                latest = search_options.get('latest_first_publish_year', '*')
                query_parts.append(f"first_publish_year:[{earliest} TO {latest}]")

            # number_of_pages: [min_number_of_pages TO max_number_of_pages]
            if 'min_number_of_pages' in search_options or 'max_number_of_pages' in search_options:
                min_pages = search_options.get('min_number_of_pages', '*')
                max_pages = search_options.get('max_number_of_pages', '*')
                query_parts.append(f"number_of_pages:[{min_pages} TO {max_pages}]")

            # Combine all query parts with AND
            full_query = ' AND '.join(query_parts)

            params = {"q": full_query, "page": pagination_key, "fields": self.book_lookup_fields}
            req = requests.get(self.book_lookup_url, params=params)
            openLibResponse = req.json()

            for book in openLibResponse["docs"]:
                title = getIfUseful(book, 'title')
                release_year = getIfUseful(book, 'first_publish_year')
                edition_docs = book.get('editions', {}).get('docs', [])
                isbn = edition_docs[0]['isbn'][0] if edition_docs and 'isbn' in edition_docs[0] else ''
                img_link = f"https://covers.openlibrary.org/a/id/{book['cover_i']}-M.jpg" if 'cover_i' in book else ''
                created_by = getIfUseful(book, "author_name")
                media_type = "book"
                item = Item(
                    book['key'], title, media_type, release_year, img_link, book['key'], created_by, isbn, release_year
                )
                response["items"].append(item)
            response["passed"] = True
            response["next_page"] = int(pagination_key) + 1
        except Exception as e:
            logging.error(f"Exception in lookup for title {title} in BookController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_book",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options,
                "url": req.url if 'req' in locals() else None,
                "response_status": req.status_code if 'req' in locals() else None,
                "response_text": req.text[:500] if 'req' in locals() else None
            })
        return response
    
    def movie_lookup(self, guid):
        params = {"api_key": self.MDB_API_KEY}
        movie = requests.get(f"{self.tmdb_base_url}/movie/{guid}", params=params).json()
        movie_id = movie.get('id', '')

        credits = requests.get(f"{self.tmdb_base_url}/movie/{guid}/credits", params=params).json()
        crew = getIfUseful(credits, 'crew', [])
        directors = []
        for crewmember in crew:
            if crewmember.get('job') == 'Director':
                directors.append(crewmember.get('name', 'Unknown Director'))
        
        title = getIfUseful( movie, 'title')
        release_year = movie.get('release_date', '0000')[:4]
        img_link = f"https://image.tmdb.org/t/p/w600_and_h900_bestv2{movie['poster_path']}" if 'poster_path' in movie else None
        language = getIfUseful(movie, 'original_language')
        summary = getIfUseful(movie, 'overview')
        duration = getIfUseful(movie, 'runtime')
        media_type = "movie"
        item = Item(
            movie_id, title, media_type, release_year, img_link, movie_id, directors, lang=language, summary=summary, duration=duration
        )

        return item
    
    def lookup_movie(self, title, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            # Required parameters
            params = {"api_key": self.MDB_API_KEY, "query": title, "page": pagination_key}

            # Add optional search parameters
            recognized_params = [
                'include_adult', 'language', 'primary_release_year', 'region', 'year'
            ]

            for param in recognized_params:
                if param in search_options:
                    params[param] = search_options[param]

            req = requests.get(f"{self.tmdb_base_url}/search/movie", params=params)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.movie_lookup, [result['id'] for result in req.json()['results']])

            for lookup in lookups:
                response['items'].append(lookup)

            response["passed"] = True
            response["next_page"] = int(pagination_key) + 1
        except Exception as e:
            logging.error(f"Exception in lookup for title {title} in MovieController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_movie",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options,
                "url": req.url if 'req' in locals() else None,
                "response_status": req.status_code if 'req' in locals() else None,
                "response_text": req.text[:500] if 'req' in locals() else None
            })
        return response

    def lookup_video_game(self, title, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            # Build where clause conditions
            where_conditions = []

            # Handle platform filter
            if 'platform' in search_options:
                platform_id = get_platform_id(search_options['platform'])
                if platform_id:
                    where_conditions.append(f"platforms = {platform_id}")

            # Handle release date filters
            # Expected format: MM/DD/YYYY
            if 'release_date_before' in search_options:
                try:
                    date_obj = datetime.strptime(search_options['release_date_before'], '%m/%d/%Y')
                    unix_timestamp = int(date_obj.timestamp())
                    where_conditions.append(f"first_release_date < {unix_timestamp}")
                except ValueError:
                    logging.warning(f"Invalid release_date_before format: {search_options['release_date_before']}")

            if 'release_date_after' in search_options:
                try:
                    date_obj = datetime.strptime(search_options['release_date_after'], '%m/%d/%Y')
                    unix_timestamp = int(date_obj.timestamp())
                    where_conditions.append(f"first_release_date > {unix_timestamp}")
                except ValueError:
                    logging.warning(f"Invalid release_date_after format: {search_options['release_date_after']}")

            # Build complete where clause if we have conditions
            where_clause = f" where {' & '.join(where_conditions)};" if where_conditions else ""

            # Build the request body, escaping quotes so the title can't break out of the search clause
            safe_title = title.replace('\\', '\\\\').replace('"', '\\"')
            offset = (int(pagination_key) - 1) * 25
            request_body = f'search "{safe_title}"; limit 25; offset {offset}; fields {self.vg_lookup_fields};{where_clause}'

            req = requests.post(self.vg_lookup_url, data=request_body, headers=self.IGDB_headers).json()
            for game in req:
                guid = game["id"]
                game_title = game["name"]
                media_type = "video_game"
                release_year = datetime.fromtimestamp(game.get('first_release_date', 0)).year
                img_link = game.get("cover", {"image_id": ""})["image_id"]
                developer = [company["company"]["name"] for company in game.get("involved_companies", [])]
                summary = game.get("summary", "")
                platforms = [platform["name"] for platform in game.get("platforms", [])]
                item = Item(
                    guid, game_title, media_type, release_year, img_link, guid, developer, summary=summary, platforms=platforms
                )
                response['items'].append(item)
            response['next_page'] = int(pagination_key) + 1
            response["passed"] = True
        except Exception as e:
            request_body_info = request_body if 'request_body' in locals() else 'Not yet formed'
            logging.error(f"Exception in lookup for title {title} in VideoGameController: {e}. Request body: {request_body_info}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_video_game",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options,
                "request_body": request_body_info
            })
        return response
    
    def lookup_board_game(self, title, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            req = requests.get(f"{self.bgg_base_url}/search", params={"query": title, "type": "boardgame"}, headers=self.bgg_header)
            root = ET.fromstring(req.content)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.board_game_detail_lookup, root)

            for lookup in lookups:
                if lookup:
                    response['items'].append(lookup)
            response['next_page'] = int(pagination_key) + 1
            response["passed"] = True
        except Exception as e:
            logging.error(f"Exception in lookup for title {title} in BoardGameController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_board_game",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options
            })
        return response

    def board_game_detail_lookup(self, child):
        item_dict = {}
        guid = child.get('id', '00000')
        item_search_req = requests.get(f"{self.bgg_base_url}/thing", params={"id": guid}, headers=self.bgg_header)
        search_root = ET.fromstring(item_search_req.content).find('./item')
        if search_root:
            names = [name.get('value') for name in search_root.iterfind('name') if name.get('type') == 'primary']
            title = names[0]
            img_link = search_root.find('./image').text if search_root.find('./image') is not None else None
            designers = [designer.get('value', 'unknown') for designer in search_root.iterfind('link') if designer.get('type') == 'boardgamedesigner']
            minimum_players = search_root.find('./minplayers').get('value')
            maximum_players = search_root.find('./maxplayers').get('value')
            year_published = search_root.find('./yearpublished').get('value')
            summary = search_root.find('./description').text
            total_duration = search_root.find('./playingtime').get('value')
            media_type = "board_game"
            item = Item(guid, title, media_type, year_published, img_link, guid, designers, summary=summary, duration=total_duration, min_players=minimum_players, max_players=maximum_players)
            return item
        else:
            return {}
    
    def lookup_rpg(self, title, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            req = requests.get(f"{self.rpggeek_base_url}/search", params={"query": title, "type": "rpgitem"}, headers=self.bgg_header)
            root = ET.fromstring(req.content)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                lookups = executor.map(self.rpg_detail_lookup, root)

            for lookup in lookups:
                if lookup:
                    response["items"].append(lookup)

            response['next_page'] = int(pagination_key) + 1
            response['passed'] = True
        except Exception as e:
            logging.error(f"Exception in lookup for title {title} in RPGController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_rpg",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options
            })
        return response

    def rpg_detail_lookup(self, child):
        item_dict = {}
        guid = child.get('id', '00000')
        item_search_req = requests.get(f"{self.rpggeek_base_url}/thing", params={"id": guid}, headers=self.bgg_header)
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
    
    def lookup_anime(self, title, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            # Build parameters dict for Jikan API
            # Jikan API available options: type, status, rating, genre, score, sfw, order_by, sort,
            # min_score, max_score, start_date, end_date, genres, genres_exclude, producers, etc.
            recognized_params = [
                'type', 'status', 'rating', 'genre', 'score', 'sfw',
                'order_by', 'sort', 'min_score', 'max_score', 'start_date',
                'end_date', 'genres', 'genres_exclude', 'producers'
            ]

            # Filter search_options to only include recognized parameters
            api_parameters = {k: v for k, v in search_options.items() if k in recognized_params}

            # Pass parameters to Jikanpy's search method
            jikan_response = self.jikan_client.search(
                "anime",
                title,
                pagination_key,
                parameters=api_parameters if api_parameters else None
            )

            if jikan_response['data']:
                for anime in jikan_response['data']:
                    item = Item(
                        anime['mal_id'],
                        anime.get('title_english'),
                        "anime",
                        anime['aired']['prop']['from']['year'],
                        anime['images']['jpg']['image_url'],
                        anime['mal_id'],
                        [studio['name'] for studio in anime['studios']],
                        summary=anime.get('synopsis'),
                        episodes=anime['episodes']
                    )
                    response['items'].append(item)
            response['next_page'] = int(pagination_key) + 1
            response['passed'] = True
        except Exception as e:
            logging.error(f"Exception in lookup for title {title} in AnimeController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_anime",
                "title": title,
                "pagination_key": pagination_key,
                "search_options": search_options,
                "api_parameters": api_parameters if 'api_parameters' in locals() else None
            })
        return response
    
    def lookup_music(self, album, pagination_key, search_options=None):
        search_options = search_options if search_options else {}
        response = {"items": [], "passed": False}
        try:
            # Build Discogs search query
            # Discogs API supports: artist, release_title, label, genre, year, format, etc.
            search_params = {'release_title': album, 'type': 'master'}

            # Add optional search parameters
            recognized_params = ['artist', 'genre', 'year', 'format', 'label', 'country', 'style']

            for param in recognized_params:
                if param in search_options:
                    search_params[param] = search_options[param]

            # Perform search
            results = self.discogs_client.search(**search_params)

            # Get the specified page of results
            page_results = results.page(pagination_key)

            for master in page_results:
                # Get full master details
                try:
                    master_id = master.id
                    full_master = self.discogs_client.master(master_id)

                    # Get the main release to access additional data like artists
                    main_release = None
                    if hasattr(full_master, 'main_release'):
                        main_release = full_master.main_release

                    # Extract artist names from main_release if available, otherwise from master data
                    artists = []
                    if main_release and hasattr(main_release, 'artists') and main_release.artists:
                        try:
                            artists = [artist.name for artist in main_release.artists]
                        except (AttributeError, TypeError) as artist_error:
                            logging.warning(f"Could not extract artist names for master {master_id}: {artist_error}")
                    elif hasattr(full_master, 'data') and 'artists' in full_master.data:
                        # Fallback to raw data if main_release doesn't have artists
                        artists = [artist['name'] for artist in full_master.data['artists'] if 'name' in artist]

                    # Get release year
                    release_year = full_master.year if hasattr(full_master, 'year') else None

                    # Get cover image (prefer the first image if available)
                    img_link = None
                    if hasattr(full_master, 'images') and full_master.images:
                        img_link = full_master.images[0]['uri']

                    # Get notes/description
                    summary = full_master.notes if hasattr(full_master, 'notes') else None

                    # Get genres (if available)
                    genres = None
                    if hasattr(full_master, 'genres') and full_master.genres:
                        genres = list(full_master.genres)

                    # Get tracklist directly from the master
                    tracklist = None
                    if hasattr(full_master, 'tracklist') and full_master.tracklist:
                        # Extract track titles from the tracklist
                        tracklist = [track.title for track in full_master.tracklist if hasattr(track, 'title')]

                    item = Item(
                        master_id,
                        full_master.title,
                        'album',
                        release_year,
                        img_link,
                        master_id,
                        artists,
                        summary=summary,
                        tracklist=tracklist,
                        genres=genres
                    )
                    response['items'].append(item)
                except Exception as master_error:
                    # If we can't get full details, skip this master
                    logging.warning(f"Could not fetch details for master {master.id}: {master_error}")
                    continue

            response['next_page'] = int(pagination_key) + 1
            response['passed'] = True
        except Exception as e:
            logging.error(f"Exception in lookup for album {album} in MusicController: {e}")
            response["exception"] = self._build_exception_dict(e, {
                "function": "lookup_music",
                "album": album,
                "pagination_key": pagination_key,
                "search_options": search_options,
                "search_params": search_params if 'search_params' in locals() else None
            })
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