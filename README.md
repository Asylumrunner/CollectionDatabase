# CollectionDatabase
A database application for cataloging my collection of physical media, powered by Python, MySQL, and a collection of APIs

## Background
Like a lot of people with nerdy sensibilities, I own a lot of physical media, from video games to movies to books to tabletop RPGs to board and card games. My apartment is positively stuffed with bookcases that are themselves stuffed with _stuff_. While this currently doesn't raise an issue, as I live in Texas where land is practically free, I would like to move into a more dense city such as Seattle, NYC, or Chicago. With that move would come a vast reduction of space, and as a necessary corollary, a vast reduction in the stuff I own.

With this in mind, I decided to convert my current static collection into more of a cycling collection, in which I only hold on to the media I plan on using/consuming in the near future, and cycling out completed media/media that no longer interests me for new stuff over time. For this strategy to work, I need to determine the subset of my current collection to "cycle out", or to sell right now with the intention of simply obtaining a new copy if and when the time comes that I actually want to play it. To fascilitate this, I decided to write a database application which can store all of the titles in my collection, allowing me to easily see what should be cycled out and cycled in at any given point. With this model, most of my physical collection is less of a collection and more of a "long term rental".

### Why Don't You Just Buy Digital Copies?
Why don't you just shut your mouth.

## Challenges
  * This database will contain fairly heterogenous data, as attributes of interest for one type of object (ex. page count) will be meaningless to some other types (ex. video games)
  * To populate data fields automatically will require the use of several publicly available APIs

## APIs In Use
  * [Giant Bomb](https://www.giantbomb.com/api/) - Giant Bomb, on top of being a video game coverage website, also has an extensive wiki populated with information about games dating back to Tennis For Two. Combined with a fairly active dev community and a well-documented API, it is the obvious first choice for collecting data about video video games
