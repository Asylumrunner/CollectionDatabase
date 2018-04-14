import sqlite3
import requests
import json
import xml.etree.ElementTree as ET
from secrets import secrets

class Collection_Database():
    def __init__(self):
        self.connection = sqlite3.connect("collection.db")
        self.cursor = self.connection.cursor()

        self.cursor.execute("CREATE TABLE IF NOT EXISTS video_games (name text, platform text, in_collection boolean, developer text);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS books (name text, author text, page_count integer, in_collection boolean);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS tabletop_rpgs (name text, publisher text, in_collection boolean);")
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

    def register_tabletop_rpg(self, title):
        req = requests.get("https://www.rpggeek.com/xmlapi2/search?query={}&type=rpgitem".format(title))
        root = ET.fromstring(req.content)

        responses_dict = {}
        for child in root:
            subelements = child.iterfind('name')
            for element in subelements:
                responses_dict[element.get('value', 'ERROR')] = child.get('id', '00000')
        book_titles = list(responses_dict.keys())

        print("The following RPG items were retrieved:")
        for x in range(len(book_titles)):
            print("{}. {}".format(x, book_titles[x]))
        print("Please indicate the number of the game to insert into the database, or QUIT")
        choice = input("Choice: ")

        invalid_choice = True
        while invalid_choice:
            if choice == "QUIT":
                return True
            else:
                try:
                    game = book_titles[int(choice)]
                    id = responses_dict[game]
                    invalid_choice = False
                except Exception:
                    print("Invalid choice")
                    choice = input("Please indicate the number of the game to insert into the database, or QUIT")

        req = requests.get("https://www.rpggeek.com/xmlapi2/thing?id={}".format(id))
        print("https://www.rpggeek.com/xmlapi2/thing?id={}".format(id))
        root = ET.fromstring(req.content)
        publishers = root.findall(".//*[@type='rpgpublisher']")
        publisher_names = [elem.get('value') for elem in publishers]

        print("This game is associated with the following publishers: ")
        for x in range(len(publisher_names)):
            print("{}. {}".format(x, publisher_names[x]))

        print("Please indicate the number of the publisher to associate with this game, or QUIT")
        choice = input("Choice: ")

        invalid_choice = True
        while invalid_choice:
            if choice == "QUIT":
                return True
            else:
                try:
                    publisher = publisher_names[int(choice)]
                    invalid_choice = False
                except Exception:
                    print("Invalid choice")
                    choice = input("Please indicate the number of the publisher to associate with this game, or QUIT")

        self.cursor.execute("INSERT INTO tabletop_rpgs VALUES(?, ?, ?);", [game, publisher, True])
        self.connection.commit()
        return True

    def register_video_game(self, title):
        GB_API_KEY = secrets['Giant_Bomb_API_Key']
        header = {'User-Agent': 'Asylumrunner_Database_Tool'}
        req = requests.get("http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game".format(GB_API_KEY, title), headers=header)
        data = req.json()

        games = [game['name'] for game in data['results']]
        print("The following games were retrieved:")
        for x in range(len(games)):
            print("{}. {}".format(x, games[x]))
        print("Please indicate the number of the game to insert into the database, or QUIT")
        choice = input("Choice: ")

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

        req = requests.get("http://www.giantbomb.com/api/game/{}/?api_key={}&format=json".format(guid, GB_API_KEY), headers=header)
        data = req.json()

        developers = [dev['name'] for dev in data['results']['developers']]
        dev_string = ", ".join(developers)

        platforms = [platform['name'] for platform in data['results']['platforms']]
        print("{} is available on the following platforms:")
        for x in range(len(platforms)):
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

    def view_video_games(self):
        self.cursor.execute("SELECT * FROM video_games ORDER BY name DESC;")
        results = self.cursor.fetchall()
        for row in results:
            print(row)

    def view_tabletop_rpgs(self):
        self.cursor.execute("SELECT * FROM tabletop_rpgs ORDER BY name DESC;")
        results = self.cursor.fetchall()
        for row in results:
            print(row)

    def wipe_database(self):
        self.cursor.execute("DROP TABLE video_games;")
        self.connection.commit()

        self.cursor.execute("DROP TABLE tabletop_rpgs;")
        self.connection.commit()
