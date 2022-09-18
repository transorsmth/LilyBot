# Lilybot (Code based off FRCDiscord/Dozer)
## Setup

### Installing PostgreSQL

You can install PostgreSQL for your platform [here](https://www.postgresql.org/download/)

### Getting your Discord Bot Token

1. Go to the [Discord Developer Portal](https://discordapp.com/developers/applications/me) and create a new application by clicking the button. Enter a name for the application when prompted.
   ![creating a new discord app](static/newapp.png)

2. Create a bot user inside your application.
   In the settings menu, go to the "Bot" menu.
   ![creating a bot user 1](static/createbot1.png)

   Within the bot menu, select the "create bot user" option.
   ![creating a bot user 2](static/createbot2.png)

3. Copy the bot user token (seen in the image below) - We'll need that later!
   Do not share your token with anyone. If someone obtains your bot user token, they gain full control of your bot. Be careful!
   ![token](static/tokens.png)

4. Within your bot user settings, make sure both "intents" settings are enabled.
   ![enabling intents](static/intents.png)


### Setting up the bot

Setup configuration options:
- LilyBot can be set up with Python.


1. Open your command line/terminal interface and go to the directory where LilyBot's code is located.
    1. If you're not familiar with how to do that:
        1. On Windows, open CMD or Powershell. On Mac and Linux, open the Terminal. and type `cd "path/to/directory"`.
           Alternatively, on Windows, go to the directory in the File Explorer app. Click the bar that is circled in the image below and type `cmd`. Press enter and the command line should open up within that directory. Also, you can use an integrated terminal with an IDE of your choice.
           ![open the cmd within a directory](static/fileExplorerBar.png)

2. Install dependencies with `python -m pip install -Ur requirements.txt` in your command line interface.
    1. If that doesn't work, try replacing `python` with `python3`.

3. Run the bot once with `python -m lilybot`. This will crash, but generate a default config file.
    1. LilyBot uses [json](http://www.json.org/) for its config file

4. Add the Discord bot account's token to `discord_token` in `config.json`

5. If you have a Google Maps API key, a Twitch API client ID and client secret, and/or a Reddit client ID and client secret, add them to the appropriate places in `config.json`. ***If you don't, your bot will still work,*** but you won't be able to use the commands that rely on these tokens.

6. Add your database connection info to `db_url` in `config.json` using the following format:

   ```postgres://user:password@host:port```

   Replace `host` with your database IP, or `localhost` if it's on the same PC. `port` is by default 5432. If the user has no password, you can remove the colon and password. The default user for the above installation is `postgres`, however we strongly suggest making a `LilyBot` user for security reasons using [this guide](https://www.postgresql.org/docs/current/app-createuser.html).

7. Add your Discord user ID, and anyone else's ID who should be able to use the developer commands, to the list `developers` in `config.json`
    1. Be careful giving this out. Developers can control everything your bot does and potentially get your [bot user token!](#getting-your-discord-bot-token)

8. The default command prefix is &. If this is already in use on your server or you would like another prefix, you can change the `prefix` value in `config.json`.

9. To configure lavalink:

* **Set the `host` and `port` values to which values that you have set up.

1. Run the bot again. You should see `Signed in as username#discrim (id)` after a few seconds.

### Adding the bot to your server

1. Within the scopes menu under OAuth2, select the "bot" scope
   ![selecting scopes](static/invite1_scopes.png)

2. A new "permissions" menu should appear below. Select all the permissions that you want your instance of LilyBot to have. If you want all permissions and you trust your instance wholeheartedly, select "Administrator"
   ![permissions](static/invite2_permissions.png)

3. The bottom of the scopes menu should have a URL. Copy and paste that URL into a new tab in your browser. It'll open a page where you can invite a bot to your server.
   ![oauthInvite](static/invite3_oauthurl.png)

### Setting up the database systems
LilyBot requires Postgres. You can set up Postgres on your own server or use a service such as ElephantSQL. To make it work in LilyBot,
install the psycopg2 pip package, then change the `db_url` key in `config.json` to a URL that follows this format:
`postgresql://username:password@host/db_name_in_postgres` with the correct information filled in.