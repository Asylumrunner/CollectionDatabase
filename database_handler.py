import sqlite3
import requests
import json
from secrets import secrets

class Collection_Database():
    def __init__(self):
        self.connection = sqlite3.connect("collection.db")
        self.cursor = self.connection.cursor()

        self.cursor.execute("CREATE TABLE IF NOT EXISTS video_games (name text, platform text, in_collection boolean, developer text);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS books (name text, author text, page_count integer, in_collection boolean);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS tabletop_rpgs (name text, in_collection boolean);")
        self.connection.commit()

    def register_item(self, table_name, key):
        if table_name == "video_games":
            self.register_video_game(key)
        elif table_name == "books":
            self.register_book(key)
        elif table_name == 'tabletop_rpgs':
            self.register_tabletop_rpg(key)
        else:
            print("Invalid table name provided. Cannot add to table")
            raise KeyError

    def register_video_game(self, title):
        GB_API_KEY = secrets['Giant_Bomb_API_Key']
        req = requests.get("http://www.giantbomb.com/api/search/?api_key={}&format=json&query="{}"&resources=game".format(GB_API_KEY, title))
        data = req.json()

        games = [game['name'] for game in data['results']]
        print("The following games were retrieved:")
        for x in range(len(games)):
            print("{}. {}".format(x, games[x]))
        choice = input("Please indicate the number of the game to insert into the database, or QUIT")

        invalid_choice = True
        while invalid_choice:
            if choice == "QUIT":
                return True
            else:
                try:
                    game = games[int(choice)]
                    guid = data['results'][int(choice)]['guid']
                    invalid_choice = False
                except Exception:
                    print("Invalid choice")
                    choice = input("Please indicate the number of the game to insert into the database, or QUIT")

        req = requests.get("http://www.giantbomb.com/api/game/{}/?api_key={}".format(guid, GB_API_KEY))
        data = req.json()

        developers = [dev['name'] for dev in data['results']['developers']]
        dev_string = ", ".join(developers)

        platforms = [platform['name'] for platform in data['results']['platforms']]
        print("{} is available on the following platforms:")
        for x in range(len(platform)):
            print("{}. {}".format(x, platforms[x]))
        choice = input("What platform is your copy? :")

        invalid_choice = True
        while invalid_choice:
            try:
                platform = platforms[int(choice)]
                invalid_choice = False
            except Exception:
                print("Invalid choice")
                choice = input("What platform is your copy? :")

        in_collection = True

        self.cursor.execute("INSERT INTO video_games VALUES(?, ?, ?, ?);", [game, platform, True, dev_string])
        self.connection.commit()
        return True
