import database_handler

db = database_handler.Collection_Database()

choice = 0

while choice != 7:

    print("1. Add item to database")
    print("2. Bulk input via text file")
    print("3. Wipe database")
    print("4. View database")
    print("5. Remove items from database")
    print("6. Export tables to CSV")
    print("7. Quit")

    choice = int(input("Select an option: "))

    if choice == 1:
        print("Adding item to database")
        print("1. Video game")
        print("2. Tabletop RPG")
        print("3. Book")
        print("4. Movie")
        print("5. Back out")
        sub_choice = int(input("Select an option: "))
        if sub_choice == 1:
            title = input("What game?: ")
            db.register_item("video_games", title)
        elif sub_choice == 2:
            title = input("What RPG?: ")
            db.register_item("tabletop_rpgs", title)
        elif sub_choice == 3:
            title = input("What book?: ")
            db.register_item("books", title)
        elif sub_choice == 4:
            title = input("What movie?: ")
            db.register_item("movies", title)
    elif choice == 2:
        file_name = input("Provide the name of the text file, including extension: ")
        with open(file_name, 'r') as in_file:
            lines = in_file.readlines()
        for line in lines:
            try:
                split_line = line.strip().split("/")
                db.register_item(split_line[1], split_line[0])
            except Exception:
                print("Exception when trying to add " + split_line[0])
    elif choice == 3:
        choice = input("Are you sure? y/n: ")
        if choice == 'y':
            db.wipe_database()
    elif choice == 4:
        db.view_video_games()
        db.view_tabletop_rpgs()
        db.view_books()
        db.view_movies()
    elif choice == 5:
        print("Removing items from database")
        print("1. Video game")
        print("2. Tabletop RPG")
        print("3. Book")
        print("4. Movie")
        print("5. Back out")
        sub_choice = int(input("Select an option: "))
        if sub_choice == 1:
            db.view_video_games()
            ids = input("List video games to remove by ID, separated by commas: ")
            db.deregister_item("video_games", ids)
        elif sub_choice == 2:
            db.view_tabletop_rpgs()
            ids = input("List tabletop RPGs to remove by ID, separated by commas:")
            db.deregister_item("tabletop_rpgs", ids)
        elif sub_choice == 3:
            db.view_books()
            ids = input("List books to remove by ID, separated by commas:")
            db.deregister_item("books", ids)
        elif sub_choice == 4:
            db.view_movies()
            ids = input("List movies to remove by ID, separated by commas:")
    elif choice == 6:
        db.export_db_to_csv()
        print("Export complete!")
