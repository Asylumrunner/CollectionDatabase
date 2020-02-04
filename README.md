# CollectionDatabase
A database application for cataloging my collection of physical media, powered by Python, SQLite3, and a collection of APIs

## Background
Like a lot of people with nerdy sensibilities, I own a lot of physical media, from video games to movies to books to tabletop RPGs to board and card games. My apartment is positively stuffed with bookcases that are themselves stuffed with _stuff_. While this currently doesn't raise an issue, as I live in Texas where land is practically free, I would like to move into a more dense city such as Seattle, NYC, or Chicago. With that move would come a vast reduction of space, and as a necessary corollary, a vast reduction in the stuff I own.

With this in mind, I decided to convert my current static collection into more of a cycling collection, in which I only hold on to the media I plan on using/consuming in the near future, and cycling out completed media/media that no longer interests me for new stuff over time. For this strategy to work, I need to determine the subset of my current collection to "cycle out", or to sell right now with the intention of simply obtaining a new copy if and when the time comes that I actually want to play it. To fascilitate this, I decided to write a database application which can store all of the titles in my collection, allowing me to easily see what should be cycled out and cycled in at any given point. With this model, most of my physical collection is less of a collection and more of a "long term rental". This also lets me get rid of objects I own and then, when the mood strikes me, rent them from a public library.

### Why Don't You Just Buy Digital Copies?
Why don't you just shut your mouth.

## Challenges
  * This database will contain fairly heterogenous data, as attributes of interest for one type of object (ex. page count) will be meaningless to some other types (ex. video games)
  * To populate data fields automatically will require the use of several publicly available APIs

## APIs In Use
  * [Giant Bomb](https://www.giantbomb.com/api/) - Giant Bomb, on top of being a video game coverage website, also has an extensive wiki populated with information about games dating back to Tennis For Two. Combined with a fairly active dev community and a well-documented API, it is the obvious first choice for collecting data about video video games
  * [BoardGameGeek](https://boardgamegeek.com/wiki/page/BGG_XML_API2) - BGG is a monolithic database for information on tabletop games, completely incomparable across the board. While their API is XML-based (I'd prefer JSON for consistency's sake), there's just no competing with their data.
  * [GoodReads](https://www.goodreads.com/api) - Goodreads is a book-centered social network, with a central focus on the collection and dispersal of user-generated book reviews. It's also a fairly large database of book information, with a fully featured API (although it too returns data in XML, grr), so it was a reasonable fit to complete the book portion of the project.
  * [The Movie Database](https://developers.themoviedb.org/3/getting-started/introduction) - The Movie Database, as its pleasantly on-the-nose name suggests, is a massive repository of data about movies, which I'm using to store my collection of physical movies. It also returns JSON, which is delightful.

## To-Dos/Feature Want List
  * Support board game collection tracking via BoardGameGeek
  * Support physical movie tracking
  * Enable the updating of collection-tracking upstream to a personal collection site, hosted on AWS S3
  * Actually, just host the whole thing on the cloud
  * Extreme stretch goal: compare the collection with the collection of my local library
  * More convenient mass editing
  * Enable movie tracking via ... some sort of API?
  * Allow for CSV <-> database version control, like some sort of "match database to CSV" and "match CSV to database" option
  * Handle weird unicode characters because game titles love to be special snowflakes
  * Add more "none of these are right" options in search results
  * Host this entire thing somewhere reasonable instead of using a CLI interface for it like a psychopath
