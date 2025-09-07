"""Initializes the bot and deals with the configuration file"""

import json
import os
import sys

import discord
from loguru import logger

config = {
    'prefix': '&', 'developers': [],
    'cache_size': 20000,
    'db_url': 'postgres://LilyBot_user:simplepass@postgres_ip',
    'chatbot_url': 'postgres://dozer_user:simplepass@postgres_ip',
    'discord_token': "Put Discord API Token here.",
    'news': {
        'check_interval': 5.0,
        'twitch': {
            'client_id': "Put Twitch Client ID here",
            'client_secret': "Put Twitch Secret Here"
        },
        'reddit': {
            'client_id': "Put Reddit Client ID here",
            'client_secret': "Put Reddit Secret Here"
        },

    },
    'lavalink': {
        'enabled': False,
        'host': '127.0.0.1',
        'port': 2333,
        'password': 'youshallnotpass',
        'identifier': 'MAIN',
        'region': 'us_central'
    },
    'debug': False,
    'presences_intents': False,
    'is_backup': False,
    'invite_override': ""
}
config_file = 'config.json'

if os.path.isfile(config_file):
    with open(config_file) as f:
        config.update(json.load(f))

with open('config.json', 'w') as f:
    json.dump(config, f, indent='\t')

if 'discord_token' not in config:
    sys.exit('Discord token must be supplied in configuration')

if sys.version_info < (3, 8):
    sys.exit('Lilybot requires Python 3.8 or higher to run. This is version %s.' % '.'.join(sys.version_info[:3]))

# logger setup
logger_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{" \
                "name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{" \
                "message}</level> "
logger.remove()
logger.add(sys.stdout, format=logger_format, level="DEBUG" if config['debug'] else "INFO", enqueue=True, colorize=True)

# noinspection PyPep8
from . import LilyBot  # After version check

intents = discord.Intents.default()
intents.members = True
intents.presences = bool(config['presences_intents'])
intents.message_content = True

bot = LilyBot(config, intents=intents, max_messages=config['cache_size'])


async def load_cogs():
    """Loads cogs for startup"""
    for ext in os.listdir('lilybot/cogs'):
        if not ext.startswith(('_', '.')):
            await bot.load_extension('lilybot.cogs.' + ext[:-3])  # Remove '.py'


bot.run()

# restart the bot if the bot flagged itself to do so
if bot._restarting:
    script = sys.argv[0]
    if script.startswith(os.getcwd()):
        script = script[len(os.getcwd()):].lstrip(os.sep)

    if script.endswith('__main__.py'):
        args = [sys.executable, '-m', script[:-len('__main__.py')].rstrip(os.sep).replace(os.sep, '.')]
    else:
        args = [sys.executable, script]
    os.execv(sys.executable, args + sys.argv[1:])
