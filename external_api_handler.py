import requests
from secrets import secrets
import xml.etree.ElementTree as ET

def get_movie(search_string):
    MDB_API_KEY = secrets['MovieDB_Key']
    req = requests.get("https://api.themoviedb.org/3/search/movie?api_key={}&query={}&include_adult=true".format(MDB_API_KEY, search_string))
    data = req.json()

    movies = [{"title": result['title'], "language":result['original_language']} for result in data['results']]
    print("The following movies were retrieved:")
    for x in range(len(movies)):
        print("{}. {}, originally in {}".format(x+1, movies[x]['title'], movies[x]['language']))
    print("Please indicate the number of the film to insert into the database, or QUIT")
    choice = input("Choice: ")

    invalid_choice = True
    while invalid_choice:
        if choice == "QUIT":
            return False
        else:
            try:
                return movies[int(choice)-1]
            except Exception:
                print("Please indicate the number of the film to insert into the database, or QUIT")
                choice = input("Choice: ")
    
def get_book(search_string):
    GR_API_KEY = secrets['Goodreads_API_Key']
    results_page = 1
    book_found = False
    while not book_found:
        print("Querying https://www.goodreads.com/search/index.xml?key={}&q={}&page={}".format(GR_API_KEY, search_string, results_page))
        req = requests.get("https://www.goodreads.com/search/index.xml?key={}&q={}&page={}".format(GR_API_KEY, search_string, results_page))
        root = ET.fromstring(req.content)

        responses_dict = {}
        results = root.find('./search/results')
        for book_listing in results:
            name = (book_listing.find('./best_book/title')).text
            responses_dict[name] = book_listing
        book_titles = list(responses_dict.keys())

        print("The following books were retrieved:")
        for x in range(len(book_titles)):
            author = responses_dict[book_titles[x]].find('./best_book/author/name').text
            print("{}. {} by {}".format(x+1, book_titles[x], author))
        print("Please indicate the number of the book to insert into the database, NONE if none of these are what you want, or QUIT")
        choice = input("Choice: ")

        invalid_choice = True
        while invalid_choice:
            if choice == "QUIT":
                return False
            elif choice == "NONE":
                results_page = results_page + 1
                invalid_choice = False
            else:
                try:
                    book = book_titles[int(choice)-1]
                    data = responses_dict[book]
                    invalid_choice = False
                    return data
                except Exception:
                    print("Invalid choice")
                    choice = input("Please indicate the number of the book to insert into the database, NONE if none of these are what you want, or QUIT")

    

def get_video_game(search_string):
    GB_API_KEY = secrets['Giant_Bomb_API_Key']
    header = {'User-Agent': 'Asylumrunner_Database_Tool'}
    req = requests.get("http://www.giantbomb.com/api/search/?api_key={}&format=json&query=%22{}%22&resources=game".format(GB_API_KEY, search_string), headers=header)
    data = req.json()

    games = [game['name'] for game in data['results']]
    release_years = [game['original_release_date'][0:4] if game['original_release_date'] else "Not Found" for game in data['results']]
    print("The following games were retrieved:")
    for x in range(len(games)):
        print("{}. {} ({})".format(x+1, games[x], release_years[x]))
    print("Please indicate the number of the game to insert into the database, or QUIT")
    choice = input("Choice: ")

    invalid_choice = True
    while invalid_choice:
        if choice == "QUIT":
            return True
        elif choice == "NONE":
            return False
        else:
            try:
                game = games[int(choice)-1]
                guid = data['results'][int(choice)-1]['guid']
                invalid_choice = False
            except Exception:
                print("Invalid choice")
                choice = input("Please indicate the number of the game to insert into the database, or QUIT")

    req = requests.get("http://www.giantbomb.com/api/game/{}/?api_key={}&format=json".format(guid, GB_API_KEY), headers=header)
    data = req.json()

    try:
        developers = [dev['name'] for dev in data['results']['developers']]
    except Exception:
        print("Trouble finding developers")
        developers = ['Not Found']
    dev_string = ", ".join(developers)

    platforms = [platform['name'] for platform in data['results']['platforms']]
    print("{} is available on the following platforms:".format(game))
    for x in range(len(platforms)):
        print("{}. {}".format(x+1, platforms[x]))
    choice = input("What platform is your copy? :")

    invalid_choice = True
    while invalid_choice:
        try:
            platform = platforms[int(choice)-1]
            invalid_choice = False
        except Exception:
            print("Invalid choice")
            choice = input("What platform is your copy? :")

    return {"name":game, "platform":platform, "developer": dev_string}

def get_tabletop_rpg(title):
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
        print("{}. {}".format(x+1, book_titles[x]))
    print("Please indicate the number of the game to insert into the database, or QUIT")
    choice = input("Choice: ")

    invalid_choice = True
    while invalid_choice:
        if choice == "QUIT":
            return True
        elif choice == "NONE":
            return False
        else:
            try:
                game = book_titles[int(choice)-1]
                id = responses_dict[game]
                invalid_choice = False
            except Exception:
                print("Invalid choice")
                choice = input("Please indicate the number of the game to insert into the database, NONE if none of these are what you want, or QUIT")

    req = requests.get("https://www.rpggeek.com/xmlapi2/thing?id={}".format(id))
    print("https://www.rpggeek.com/xmlapi2/thing?id={}".format(id))
    root = ET.fromstring(req.content)
    publishers = root.findall(".//*[@type='rpgpublisher']")
    publisher_names = [elem.get('value') for elem in publishers]

    print("This game is associated with the following publishers: ")
    for x in range(len(publisher_names)):
        print("{}. {}".format(x+1, publisher_names[x]))

    print("Please indicate the number of the publisher to associate with this game, or QUIT")
    choice = input("Choice: ")

    invalid_choice = True
    while invalid_choice:
        if choice == "QUIT":
            return True
        elif choice == "NONE":
            return False
        else:
            try:
                publisher = publisher_names[int(choice)-1]
                invalid_choice = False
            except Exception:
                print("Invalid choice")
                choice = input("Please indicate the number of the publisher to associate with this game, or QUIT")
    data_dict = {
        'publisher': publisher,
        'game': game
    }

    return data_dict

def write_to_fail_file(title, type):
    with open('failed_entries.txt', 'a') as file:
        file.write(title + "/" + type)
