"""Given an arbitrary RSS feed, get new posts from it"""

import datetime
import re
import xml.etree.ElementTree

import aiohttp
import discord

from .AbstractSources import Source


def clean_html(raw_html):
    """Clean all HTML tags.
    From https://stackoverflow.com/questions/9662346/python-code-to-remove-html-tags-from-a-string"""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class RSSSource(Source):
    """Given an arbitrary RSS feed, get new posts from it"""
    url = None
    color = discord.colour.Color.blurple()
    date_formats = ["%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S %Z"]  # format for datetime.strptime()
    base_url = None
    read_more_str = "...\n Read More"

    def __init__(self, aiohttp_session: aiohttp.ClientSession, bot):
        super().__init__(aiohttp_session, bot)
        self.guids_seen = set()

    async def first_run(self):
        """Fetch the current posts in the feed and add them to the guids_seen set"""
        response = await self.fetch()
        self.parse(response, True)

    async def get_new_posts(self):
        """Fetch the current posts in the feed, parse them for data and generate embeds/strings for them"""
        response = await self.fetch()
        items = self.parse(response)
        new_posts = {
            'source': {
                'embed': [],
                'plain': []
            }
        }
        for item in items:
            data = self.get_data(item)
            new_posts['source']['embed'].append(self.generate_embed(data))
            new_posts['source']['plain'].append(self.generate_plain_text(data))
        return new_posts

    async def fetch(self):
        """Use aiohttp to get the source feed"""
        response = await self.http_session.get(url=self.url)
        return await response.text()

    def parse(self, response, first_time=False):
        """Use xml ElementTrees to get individual Elements for new posts"""
        new_items = set()
        root = xml.etree.ElementTree.fromstring(response)
        channel = root[0]
        for child in channel:
            if child.tag == 'item':
                guid = child.find('guid')
                if first_time:
                    self.guids_seen.add(guid.text)
                    continue
                new = self.determine_if_new(guid.text)
                if new:
                    new_items.add(child)
        return new_items

    def determine_if_new(self, guid):
        """Given a RSS item's guid, determine if this item is new or not. Store GUID if new."""
        if guid not in self.guids_seen:
            self.guids_seen.add(guid)
            return True
        else:
            return False

    def get_data(self, item):
        """Given a xml Element, extract it into readable data"""
        types = {
            'title': 'title',
            'url': 'url',
            '{http://purl.org/dc/elements/1.1/}creator': 'author',
            'description': 'description'
        }
        data = {}
        for key, value in types.items():
            element = item.find(key)
            if element is not None:
                data[value] = element.text
            else:
                data[value] = None

        if data['url'] is None:
            if item.find('link') is not None:
                data['url'] = item.find('link').text
            elif item.find('guid').attrib['isPermaLink'] == 'true':
                data['url'] = item.find('guid').text

        date_string = item.find('pubDate')
        if date_string is not None:
            formatted = False
            for date_format in self.date_formats:
                try:
                    data['date'] = datetime.datetime.strptime(date_string.text, date_format)
                    formatted = True
                except ValueError:
                    continue
            if not formatted:
                data['data'] = datetime.datetime.now()
        else:
            data['date'] = datetime.datetime.now()

        desc = clean_html(data['description'])
        # length = 1024 - len(self.read_more_str)
        length = 500
        if len(desc) >= length:
            data['description'] = desc[0:length] + self.read_more_str
        else:
            data['description'] = desc

        return data

    def generate_embed(self, data):
        """Given a dictionary of data, generate a discord.Embed using that data"""
        embed = discord.Embed()
        embed.title = f"New Post From {self.full_name}!"
        embed.colour = self.color

        embed.description = f"[{data['title']}]({data['url']})"

        embed.url = self.base_url

        embed.add_field(name="Description", value=data['description'])

        embed.set_author(name=data['author'])

        embed.timestamp = data['date']

        return embed

    def generate_plain_text(self, data):
        """Given a dictionary of data, generate a string using that data"""
        return f"New Post from {self.full_name} from {data['author']}:\n" \
               f"{data['title']}\n" \
               f">>> {data['description']}\n" \
               f"Read more at {data['url']}"


class TestSource(RSSSource):
    """A source for testing. Make sure to disable this before committing."""
    url = "http://lorem-rss.herokuapp.com/feed?interval=1"
    base_url = "http://lorem-rss.herokuapp.com"
    full_name = "Test Source"
    short_name = "test"
    description = "Test Source Please Ignore"
    disabled = True
