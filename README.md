# BoardGameClub
Project 4 of the Full Stack Nanodegree <br>
Michal Pytlos, July 2018

## 1. Overview
### 1.1. Program features
This program is meant to serve as a web application for a board game club and offers the following functionalities:
1. Home page:
  * **Non-authenticated users:** display info about the club, list its members, list games in the club's collection, display users' posts.
  * **Authenticated users:** all above and add new posts, edit or delete authored posts.
  * **Club admins:** all above and modify club's game collection, edit club info.
2. User profile page:
  * **Non-owners:** display info about the user, list games in the user's collection.
  * **Profile owner:** all above and edit profile info, delete profile, modify user's game collection.
3. Game page:
  * **Non-authenticated users:** display game info, list game owners.
  * **Authenticated users:** all above and update game info.
4. Game-finder page:
  *  **All users:** list all games satisfying the provided search criteria.
5. Game API endpoint:
  * **All users:** list games, with all their attributes, satisfying the criteria provided in the query string. The response is in JSON.
6. Info API endpoint:
  * **All users:** provide basic information on all game-categories, users and games held in the database. The response is in JSON.

### 1.2. Key design features
* Built with the [Flask](http://flask.pocoo.org/) web framework.
* Web pages generated with the [Jinja2](http://jinja.pocoo.org/) template engine.
* App's data managed using [SQLAlchemy](https://www.sqlalchemy.org/).
* User authentication managed by [Google Sign-In for server-side apps](https://developers.google.com/identity/sign-in/web/server-side-flow).
* Synchronizer Token Pattern implemented to protect from CSRF attacks.
* Information on new games obtained automatically from [BGG XML API2](https://boardgamegeek.com/wiki/page/BGG_XML_API2).
* Requests changing state of existing resources require authorisation.
* JSON API endpoints.

## 2. Installation

Python 2.7 (available from [python.org](https://www.python.org/downloads/)) is required to install and run the application.

### To install and configure the application, do the following:

#### 1. Create source distribution
Navigate to the directory containing **setup.py** and run: `python setup.py sdist`

This command creates an archive of the default format for the current platform. For Unix and version 1.0 of the application, the created archive file will be a gzipped tarball named **boardgameclub-1.0.tar.gz**. For more information on creating source distributions from **setup.py** see [python.org](https://docs.python.org/2/distutils/sourcedist.html).

#### 2. Install application
Run: `pip install <path/to/archive>`

This will install **boardgameclub** with its dependecies and two command line tools: **bgc_add_admin** and **bgc_init_db**. Consider using an isolated environment such as **virtualenv** for this application in order to avoid dependency conflicts. For more information on **virtualenv** see [virtualenv.pypa.io](https://virtualenv.pypa.io/en/latest/).

#### 3. Create instance folder
The application expects the configuration and client secret files to be located in the instance folder. The instance folder has to be created manually at a specific path: **$PREFIX/var/boardgameclub-instance** where on Unix **$PREFIX** is **/usr** or the path to your virtualenv.

The expected path to the instance folder is an attribute of the app: **Flask.instance_path**. To check the value of this attribute:
1. Start the python interpreter
2. Import the app: `from boardgameclub import app`
3. Get the value: `app.instance_path`

For more information about instance folders and how to change their default location see [flask.pocoo.org](http://flask.pocoo.org/docs/1.0/config/#instance-folders).

#### 4. Create config file
Default application settings from **boardgameclub.default_settings** are overridden by the contents of a separate configuration file, **config.py** located in the instance folder, if it exists.

Create **config.py** file in the instance folder and set **SECRET_KEY** to your own value.
To use your own database, set **DB_URL** to the value as per [docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls). See also [flask.pocoo.org](http://flask.pocoo.org/docs/1.0/config/#builtin-configuration-values) for a list of configration values used internally by Flask and therefore available in **boardgameclub**.

#### 5. Create OAuth 2.0 client ID and client secret
  1. Go to https://console.developers.google.com/apis
  2. From the project drop-down on the top, create a new project by selecting **NEW PROJECT**.
  2. From the project drop-down, select the new project.
  3. Select **credentials** from the menu on the left.
  4. Go to **OAuth consent screen** and configure the consent screen.
  5. Go to **Credentials** and select **OAuth client ID** from the **create credentials** drop-down menu.
  5. Select **web application**.
  6. Set **Authorized JavaScript origins** to the origin URI of your instance of the boardgameclub application
  7. Set **Authorized redirect URIs** to the same value as above
  8. Press **Create**.
  9. Download the client secret JSON file, rename it to **client_secret.json** and move it to the instance folder.

## 3. Getting started

### 3.1. Starting the app
To start the Flask's built-in development server run: `python -m boardgameclub`

### 3.2. Initializing database
To initalize your new database run: `bgc_init_db`

### 3.3. Adding club admins
To add a club admin run: `bgc_add_admin` and follow the instructions.

### 3.3. Web pages
* Home page URL: `http://<authority>`
* All other app's pages can be accessed using the navigation bar and the page-embedded links.

## 4. API endpoints
### 4.1. Game API endpoint
* URL: `http://<authority>/api/games`
* Serves information on games satisfying the criteria provided in the query string.
#### Getting info on an arbitrary game
* To get info about an arbitrary game, specify it's id in the query string; for example:
  * `http://<authority>/api/games?id=1` returns info on the game with id=1.
  * `http://<authority>/api/games?id=3&id=7&id=8` returns info on the games with id in (3, 7, 8).       
* To find id's of all the games in database, use the Info API endpoint: `http://<authority>/api/info?games=1`
#### Complex queries
* Valid query args are of two types: ownership type and game-attribute type. The endpoint first builds two sets of games, ownership set with games satisfying the ownership criteria and game-attribute set with games satisfying the game-attribute criteria; an intersection of these two sets is then returned to the user. Specifying no criteria of a given type will result in the corresponding set with all the games in the database.
* Valid arguments of the **ownership** type are given in the table below:

| Argument              | Description                         |Multiple args|
| ----------------------| ------------------------------------|-------------|
| club=1                | include all games owned by the club |NO           |
| user=INTEGER (user id)| include all games owned by this user|YES          |

* Valid arguments of the **game-attribute** type are given in the table below:

| Argument                      | Description                                      |Multiple args|
| ------------------------------| -------------------------------------------------|-------------|
| id=INTEGER                    | only include game with this id                   | YES         |
| name=STRING                   | include only games with this name                | NO          |
| category=INTEGER (category id)| include only games belonging to this category    | YES         |
| rating-min=[1-10]             | include only games with rating >= this           | NO          |
| players-from=INTEGER          | see [1]                                          | NO          |
| players-to=INTEGER            | see [1]                                          | NO          |
|time-from=INTEGER (minutes)    | see [2]                                          | NO          |
|time-to=INTEGER (minutes)      | see [2]                                          | NO          |
|weight-min=[1-5]               | include only games with complexity rating >= this| NO          |
|weight-max[1-5]                | include only games with complexity rating <= this| NO          |

[1] Include only games with number of players interval containing [players-from, players-to] interval. For the query to be accepted either both or none of these two arguments must be specified. <br>
[2] Include only games with playing time interval intersecting [time-from, time-to] interval. The default values of players-from and players-to are zero and infinity respectively.
#### Example complex query string
* `?club=1&user=1&user=2&category=3&category=4&rating-min=7` would result in the following:
  * {ownership set} = {games owned by the club} ∪ {games owned by user 1} ∪ {games owned by user 2}
  * {game-attribute set} = {games belonging to category 3 or 4} ∩ {games with rating >= 7}
  * {game set returned by the API} = {ownership set} ∩ {game-attribute set}

### 4.2. Info API endpoint
* URL: `http://<authority>/api/info`
* Provides basic information on game-categories, users and games held in the database.
* Valid arguments are given in the table below:

| Argument    | Description                             |
| ----------- | ----------------------------------------|
| users=1     | return basic info on all users          |
| categories=1| return basic info on all game categories|
| games=1     | return basic info on all games          |

## 5. File structure

File structure of the program is outlined below.

```
setup.py
MANIFEST.in
README.md
boardgameclub/
  __init__.py
  __main__.py
  default_settings.py
  views.py
  database.py
  models.py
  scripts/
    __init__.py
    add_admin.py
    init_db.py
  data/
    bgclub.db
  static/
    ajaxForm.js
    signIn.js
    style.css
  templates/
```

Chosen files and directories are briefly described in the table below.

| File/directory      | Description                                            |
|---------------------| -------------------------------------------------------|
| default_settings.py | Default settings for the application                   |
| views.py            | View functions, csrf protection, authentication and authorisation |
| database.py         | SQLAlchemy engine configuration                        |
| models.py           | Model and table definitions                            |
| scripts/            | Directory containing scripts registered as command line tools during package installation|
| init_db.py          | Creates and initializes a new database for the club    |
| add_admin.py        | Adds a club admin                                      |
| bgclub.db           | Example SQLite database                                |
| static/             | Directory containing static files                      |
| ajaxForm.js         | JS code managing forms and ajax requests to the server |
| signIn.js           | JS code managing Google sign-in                        |
| style.css           | Styling                                                |
| templates/          | Directory containing Jinja2 HTML templates             |
