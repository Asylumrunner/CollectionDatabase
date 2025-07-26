# Project To-Do List

## Data Setup
* Bulk download datasets
    * Anime - MAL scraping seems possible
    * Movies - TMDB dataset via Kaggle
    * Video Games - ????
    * Board Games - Kaggle has this dataset too
    * Role-Playing Games
    * Albums - Musicbrainz
    * Books - OpenLibrary provided
* Make sure my DB instance is even large enough to handle it lmao
* Set up... some sort of automated data updater?
* Reconfigure SearchWorker into DbSearchWorker, read exclusively from table

## Basic Database Operations
* Item creation data flow
    * Insert item into items table and appropriate subtable
* Item details data flow
    * Get row from items table and relevant subtable
* Item Insertion data flow
    * Create row in item ownership table
* Item Deletion data flow
    * Remove row in item ownership table
* User creation flow
    * Add row to users table
* User deletion flow
    * Remove row from users table
    * Remove all rows associated with user from item ownership, lists table
    * Remove list items associated with deleted lists from table
* List creation flow
    * Add row to lists table
* List deletion flow
    * Remove row from lists table
    * Remove rows from list items table associated with list
* Add item to list flow
    * Confirm existence of item in items table
    * Add row to list items table
* Remove item from list flow
    * Remove row from list items table

## Data Validation
* Update data validators for the new item fields

## Security
* Make sure people can only get the shit they're supposed to

## Caching
* Set up a caching layer for expensive database operations

## Testing
* Set up `testing.mysqld` and enable a command-line option to spin up and connect to a mock MySQL instance rather than the real one
