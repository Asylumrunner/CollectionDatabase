import database_handler

db = database_handler.Collection_Database()

choice = 0

while choice != 4:

    print("1. Add item to database")
    print("2. Wipe database")
    print("3. View video_game table")
    print("4. Quit")

    choice = int(input("Select an option: "))

    if choice == 1:
        print("Adding item to database")
        print("1. Video game")
        print("2. Tabletop RPG")
        print("3. Back out")
        sub_choice = int(input("Select an option: "))
        if sub_choice == 1:
            title = input("What game?: ")
            db.register_item("video_games", title)
        elif sub_choice == 2:
            title = input("What RPG?: ")
            db.register_item("tabletop_rpgs", title)
    elif choice == 2:
        db.wipe_database()
    else:
        db.view_video_games()
        db.view_tabletop_rpgs()
