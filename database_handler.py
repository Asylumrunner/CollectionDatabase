import sqlite3
import requests
import json
import csv
import external_api_handler as apis
import xml.etree.ElementTree as ET
from secrets import secrets
from tabulate import tabulate

class Collection_Database():
    def __init__(self):
        self.connection = sqlite3.connect("collection.db")
        self.cursor = self.connection.cursor()

        self.cursor.execute("CREATE TABLE IF NOT EXISTS video_games (uid INTEGER PRIMARY KEY, name text, platform text, in_collection boolean, developer text);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS books (uid INTEGER PRIMARY KEY, name text, author text, isbn text, in_collection boolean);")
        self.connection.commit()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS tabletop_rpgs (uid INTEGER PRIMARY KEY, name text, publisher text, in_collection boolean);")
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

    def deregister_item(self, table_name, ids):
        self.cursor.execute("DELETE FROM {} WHERE uid IN ({});".format(table_name, ids))
        self.connection.commit()

    def register_book(self, title):
        data = apis.get_book(title)
        if data:
            book = (data.find('./best_book/title')).text
            author = (data.find('./best_book/author/name')).text
            self.cursor.execute("INSERT INTO books (name, author, in_collection) VALUES(?, ?, ?);", [book, author, True])
            self.connection.commit()
        return True

    def register_tabletop_rpg(self, title):
        data = apis.get_tabletop_rpg(title)
        if data:
            self.cursor.execute("INSERT INTO tabletop_rpgs (name, publisher, in_collection) VALUES(?, ?, ?);", [data['game'], data['publisher'], True])
            self.connection.commit()
        return True

    def register_video_game(self, title):
        data = apis.get_video_game(title)
        if data:
            self.cursor.execute("INSERT INTO video_games (name, platform, in_collection, developer) VALUES(?, ?, ?, ?);", [data['name'], data['platform'], True, data['developer']])
            self.connection.commit()
        return True

    def get_book_table(self):
        self.cursor.execute("SELECT * FROM books ORDER BY name DESC;")
        results = self.cursor.fetchall()
        return results

    def get_rpg_table(self):
        self.cursor.execute("SELECT * FROM tabletop_rpgs ORDER BY name DESC;")
        results = self.cursor.fetchall()
        return results

    def get_video_game_table(self):
        self.cursor.execute("SELECT * FROM video_games ORDER BY name DESC;")
        results = self.cursor.fetchall()
        return results

    def view_video_games(self):
        results = self.get_video_game_table()
        results_as_lists = []
        for row in results:
            results_as_lists.append(list(row))
        print(tabulate(results_as_lists, headers=['ID', 'Name', 'Platform', 'In Collection?', 'Developer']))

    def view_tabletop_rpgs(self):
        results = self.get_rpg_table()
        results_as_lists = []
        for row in results:
            results_as_lists.append(list(row))
        print(tabulate(results_as_lists, headers=['ID', 'Name', 'Publisher', 'In Collection?']))

    def view_books(self):
        results = self.get_book_table()
        results_as_lists = []
        for row in results:
            results_as_lists.append(list(row))
        print(tabulate(results_as_lists, headers=['ID', 'Name', 'Author', 'In Collection?']))

    def export_db_to_csv(self):
        with open('books.csv', 'w', newline='') as books_csv:
            book_writer = csv.writer(books_csv, dialect='excel')
            results = self.get_book_table()
            for row in results:
                book_writer.writerow(list(row))
        with open('games.csv', 'w', newline='') as games_csv:
            game_writer = csv.writer(games_csv, dialect='excel')
            results = self.get_video_game_table()
            for row in results:
                game_writer.writerow(list(row))
        with open('rpgs.csv', 'w', newline='') as rpgs_csv:
            rpg_writer = csv.writer(rpgs_csv, dialect='excel')
            results = self.get_rpgtable()
            for row in results:
                rpg_writer.writerow(list(row))

    def wipe_database(self):
        self.cursor.execute("DROP TABLE video_games;")
        self.connection.commit()

        self.cursor.execute("DROP TABLE tabletop_rpgs;")
        self.connection.commit()

        self.cursor.execute("DROP TABLE books;")
        self.connection.commit()
