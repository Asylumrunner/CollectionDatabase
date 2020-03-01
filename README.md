# CollectionDatabase
A database application for cataloging my collection of physical media, powered by Python, AWS Lambda, DynamoDB, Flask, Zappa, and a collection of APIs

## Table of Contents
1. [Background](https://www.github.com/Asylumrunner/CollectionDatabase#overview)
2. [Tech Stack](https://www.github.com/Asylumrunner/CollectionDatabase#tech-stack)
3. [APIs In Use](https://www.github.com/Asylumrunner/CollectionDatabase#apis-in-use)
4. [Architecture](https://www.github.com/Asylumrunner/CollectionDatabase#architecture)
5. [Endpoint Documentation](https://www.github.com/Asylumrunner/CollectionDatabase#endpoint-documentation)

## Background
Like a lot of people with nerdy sensibilities, I own a lot of physical media, from video games to movies to books to tabletop RPGs to board and card games. I've found that having a large digital record of this collection is fairly useful for a variety of reasons, including but not limited to:

* Keeping track of all of this stuff when I take it all on a cross-country move
* Knowing what stuff I have while I'm out and about shopping so I don't buy a book I already own again like a humongous doofus
* Being able to hand a list of games/movies/books to a friend and ask "what do you recommend I play/watch/read next?" instead of having to try to hastily remember all the stuff you own
* Having programmatic access to this collection could help another project in which I build a recommendation engine, using my own preferences as a data set
* I dunno I like writing APIs

So, for all of these reasons, I built this API, designed to be able to look up collection items (the clumsy catch-all term I'm going to use, as a more official-sounding synonym for "my crap"), and offer CRUD operations with a DynamoDB database to maintain a digital signature of this collection. 

### Why Don't You Just Buy Digital Copies?
Because I'm a psychopath who likes having a big physical pile of stuff.

## Tech Stack
This project was created in Python 3.6, with the actual RESTful API scaffolding provided by Flask 1.1.1. This project was designed to run in the cloud, using AWS API Gateway to connect to the API, deployed as an AWS Lambda function, which in turn connects to a DynamoDB database. However, it runs perfectly fine on local as well. Deployment of the API to the cloud is handled via Zappa, and retrieval of data for all of the various collection items is handled by a bundle of miscellanious public APIs, described below. Backups of the database are stored in S3 (see Endpoint Documentation below for details).

## APIs In Use
  * [Giant Bomb](https://www.giantbomb.com/api/) - Giant Bomb, on top of being a video game coverage website, also has an extensive wiki populated with information about games dating back to Tennis For Two. Combined with a fairly active dev community and a well-documented API, it is the obvious first choice for collecting data about video video games
  * [BoardGameGeek](https://boardgamegeek.com/wiki/page/BGG_XML_API2) - BGG is a monolithic database for information on tabletop games, completely incomparable across the board. While their API is XML-based (I'd prefer JSON for consistency's sake), there's just no competing with their data. I'm using this for both board games and tabletop RPGs.
  * [GoodReads](https://www.goodreads.com/api) - Goodreads is a book-centered social network, with a central focus on the collection and dispersal of user-generated book reviews. It's also a fairly large database of book information, with a fully featured API (although it too returns data in XML, grr), so it was a reasonable fit to complete the book portion of the project.
  * [The Movie Database](https://developers.themoviedb.org/3/getting-started/introduction) - The Movie Database, as its pleasantly on-the-nose name suggests, is a massive repository of data about movies, which I'm using to store my collection of physical movies. It also returns JSON, which is delightful.
  * [Seattle Public Library API](https://data.seattle.gov/Community/Library-Collection-Inventory/6vkj-f5xf) - In a pleasant surprise for local government, Seattle's public library system has made their entire collection available in queryable form via API, which is nice! I use this to cross-compare my collection of books with those of the Seattle public library system, to identify books I can sell to save space.

## Architecture
This API functions by use of a custom interface called GenreController, which represents a class used to perform API lookups and CRUD operations on a database for one "genre" of collection item each (that is, there's a BookController, MovieController, etc.).

As you might know, Python doesn't _technically_ have interfaces. However, the ABC (AbstractBaseClass) library included in base Python does allow you to essentially fake them by creating a parent class with entirely abstract methods, and in my mind the ability to extend this API down the line with new kinds of collection items (say, records or CDs) was more valuable to me than adhering to language dogma.

The main API controller maintains a collection of these GenreController objects, maintained in a dictionary and keyed by the name of their genre ('books', 'movies', etc). Most API endpoints follow a pattern of grabbing the genre from the request path, and using that to invoke the correct GenreController to make the operation. Individual calls to the API must be of homogenous genre; that is, if you want to add a book, a movie, and a video game, that must be 3 API calls, however adding three books can be done in 1.

This API makes pretty liberal use of multithreading, since there are a _lot_ of GET calls to random public APIs in here, so I didn't want to bottleneck on them as bad. It is, admittedly, a pretty first-pass implementation of concurrency, so it's possible greater optimizations could be made, but real-world performance is currently tolerably fast for me.

## Endpoint Documentation

#### GET /lookup/\<media>/\<title>

Looks up a collection item via the appropriate public API, returning results of a search query for the item. What data is returned depends on the kind of item (video games don't have ISBNs, for example), but all items have a name, an original_guid, which is their guid as assigned by the source API, and a guid, which is the original_guid prefixed by a unique key based on the GenreController ('BK-', 'BG-', 'VG-', 'RP-', or 'MV-').

##### Request Parameters
```
media - The genre of collection item to add. Must be one of ['books', 'movies', 'video_game', 'board_game' or 'rpg']
title - The title of the collection item to be looked up. 
```

##### Example Response
```
[
  {
    'guid': string,
    'original-guid': string,
    'name': strng,
    'release_year': string,
    'platform': [string] (video games only),
    'summary': string,
    'author': string (books only),
    'isbn': string (books only),
    'language': string (movies only),
    'duration': string (movies, board games only),
    'minimum_players': string (board games only),
    'maximum_players': string (board games only)
  },
  {}.
  ...
]
```

#### GET /lookup/bulk/\<media>

As above, but performs parallel lookups of multiple titles provided as a list in the body of the request. Also has a 'picky' option, default false, that when enabled will only return the best individual lookup result per item, as determined by comparing the title value input with the title of the result with fuzzy string comparison.

##### Request Parameters
```
media - The genre of collection item to add. Must be one of ['books', 'movies', 'video_game', 'board_game' or 'rpg']
```

##### Request Body
```
{
  'titles' ([string]): REQUIRED - a list of collection item titles, as strings, to look up
  'picky' (boolean): whether or not to filter lookup results down to the single best   result, as defined by a fuzzy string match between titles. Default false
}
```

##### Example Response
```
[
  [
    {
      'guid': string,
      'original-guid': string,
      'name': strng,
      'release_year': string,
      'platform': [string] (video games only),
      'summary': string,
      'author': string (books only),
      'isbn': string (books only),
      'language': string (movies only),
      'duration': string (movies, board games only),
      'minimum_players': string (board games only),
      'maximum_players': string (board games only)
    },
    {}.
    ...
  ],
  [
    {},
    {},
    {}
  ],
  [],
  ...
]
```

#### PUT /\<media>/\<key>
Retrieves data from the relevant public API for the public key, creates a database object with that data, and inserts the key into DynamoDB.

##### Request Parameters
```
media - The genre of collection item to add. Must be one of ['books', 'movies', 'video_game', 'board_game' or 'rpg']
key - the original_guid parameter of a lookup response, NOT the title. Note that this is the original_guid, lacking the appended prefix
```

##### Example Response
```
"Key <key> was inserted successfully"
```

#### PUT /backup
Each GenreController reads every single entry it has in the DynamoDB table, filters it into a list of GUIDs, and saves those lists of GUIDs into S3.

##### Example Response
```
{
  'failed_backups': int,
  'successful_backups': int,
  'error_messages': [
    {
      'Controller': string,
      'error_message': string
    },
    {},
    ...
  ]
}
```

#### PUT /restore
Each GenreController reads the backup files inserted into S3 with /backup, and inserts those GUIDs back into the database. Note that, in the current implementation, this will leave the database as a union of whatever was in it before and whatever was in the backup file. Options to tweak this behavior are coming.

##### Example Response
```
{
  'failed_restores': int,
  'successful_restores': int,
  'error_messages': [
    {
      'Controller': string,
      'error_message': string
    },
    {},
    ...
  ]
}
```

#### GET /lib-compare/\<media>/\<key>
A special endpoint which currently only works with books. This endpoint will take either a key for a book object in the database, or every book in the database, and query for their ISBN(s) in a public library database, looking for matches. Currently, this only works with the Seattle Public Library system.

##### Request Parameters
```
media - The genre of collection item to add. Must be 'books'
key - the original_guid parameter of a lookup response, NOT the title. Note that this is the original_guid, lacking the appended prefix. If missing, this endpoint searches for every book in the database
```

##### Example Response
```
{
  'lookup_response': [
    {
      "DB_Item": {
        'guid': string,
        'original-guid': string,
        'name': strng,
        'release_year': string,
        'summary': string,
        'author': string,
        'isbn': string
      },
      "Library_Item": {
          "author": string,
          "bibnum": string",
          "floatingitem": string,
          "isbn": string,
          "itemcollection": string,
          "itemcount": string,
          "itemlocation": string,
          "itemtype": string,
          "publicationyear": string,
          "publisher": string,
          "reportdate": string,
          "subjects": string,
          "title": string
        }
      },
      "match": boolean,
      "status": string
    },
    {},
    ...
  ]
}
```

## To-Dos

* Add picky option to single item lookup
* Make backups less wonky/provide more control as to how backups work



