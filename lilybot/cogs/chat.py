"""Records members' XP and level."""
import asyncio
from loguru import logger
import re

import aiohttp
import discord
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer, ChatterBotCorpusTrainer
from discord.ext.commands import guild_only, has_permissions, UserInputError
from discord.ext.tasks import loop
from sentry_sdk import capture_exception

from ._utils import *
from .. import db
from ..components.ChatbotChannel import ChatbotChannel, ChatbotChannelCache
from ..components.ChatbotCustom import ChatbotCustom
from ..components.ChatbotTraining import ChatbotTraining
from ..components.ChatbotUser import ChatbotUserCache, ChatbotUser
from ..context import LilyBotContext
from ..utils import clean

globalratelimit = 2
clearcache = True
cachelimit = 1000
blurple = discord.Color.blurple()


class Chat(Cog):
    """Commands and event handlers for chatting with the bot"""

    def __init__(self, bot):
        super().__init__(bot)
        self._loop = bot.loop
        self.chatbot_url = bot.config['chatbot_url']
        self.session = aiohttp.ClientSession(loop=bot.loop)

        self.chatbot_object = ChatBot(
            'Fred',
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            logic_adapters=[
                'chatterbot.logic.BestMatch'
            ],
            database_uri=self.chatbot_url
        )
        self.trainer = ListTrainer(self.chatbot_object)
        self._channel_cache = {}
        self._user_cache = {}
        self._custom_cache = {}

        self.next_responses = {}

    @Cog.listener("on_ready")
    async def on_ready(self):
        """reset processing and preload cache when connected"""
        await db.Pool.execute("""
            UPDATE chatbot_channels
            SET processing = 0
            WHERE true;
        """)

        # await self.preloadcache()

    async def train_process(self, a, b):
        """Makes a new chatterbot object and trains it. """
        self.trainer.train([a, b])

    async def respond_process(self, a):
        """Makes a new chatterbot object and gets the response to the statement"""
        bot_input = self.chatbot_object.get_response(a)
        await asyncio.sleep(2)
        return str(bot_input)

    @dev_check()
    @command()
    async def send(self, ctx, channel_id, *, text: str):
        """Dev only command to send messages"""
        channel = await ctx.bot.fetch_channel(int(channel_id))
        await channel.send(text)
        await ctx.reply(
            embed=discord.Embed(title=f"Message sent to #{channel.name}", description=f"Message content: {text}"))

    @dev_check()
    @command()
    async def setnext(self, ctx, guild_id, *, text: str):
        """Dev magic"""
        self.next_responses[int(guild_id)] = text
        guild = await ctx.bot.fetch_guild(int(guild_id))
        await ctx.send(f"The next time the bot responds in {guild.name} respond with \"{text}\"")

    @command(name='train')
    async def usertrain(self, ctx):
        """Allows users to add custom training to the bot"""
        message = ctx.message
        user = await self.load_user(ctx.author.id)

        if user.banned:
            await message.channel.send('You are banned from training the chatbot to ensure the safety of other users.')
            return

        if f'{ctx.prefix}trigger' not in message.content:
            await message.channel.send(f'You are missing your {ctx.prefix}trigger argument.')
            # check to see if trigger is present
            return

        if f'{ctx.prefix}response' not in message.content:
            await message.channel.send(f'Sorry it appears that you are missing your {ctx.prefix}response argument. ')
            # check to see if response is present
            return

        part1re = re.search(f'{ctx.prefix}trigger(.*){ctx.prefix}response', message.content).group(0)
        part1 = part1re[8:].replace(f'{ctx.prefix}response', '')
        part1 = part1.replace("\n", "/n")
        # trim the regex statement to the necessary part

        part2 = message.content.partition(f'{ctx.prefix}response')[2]
        part2 = part2.replace("\n", "/n")
        # get the part after -response
        if len(part1.replace(' ', '')) < 1:
            await ctx.send(
                'Your trigger looks like its either all spaces or has like 1 character in it. Maybe try again with '
                'more real characters?')
            return
            # make sure it isnt all spaces or 1 letter
        if len(part2.replace(' ', '')) < 1:
            await ctx.send(
                'Your response looks like its either all spaces or has like 1 character in it. Maybe try again with '
                'more real characters?')
            return
            # make sure it isn't all spaces or 1 letter
        part1 = part1.strip()
        part2 = part2.strip()
        embed = discord.Embed(title="Training:", color=discord.Color.orange())
        embed.add_field(name="Trigger", value=part1.replace("/n", "\n"))
        embed.add_field(name="Response", value=part2.replace("/n", "\n"))
        msg = await ctx.send(embed=embed)
        await self.train_process(part1, part2)
        embed.title = "Trained:"
        embed.colour = discord.Color.green()
        await msg.edit(embed=embed)
        await ChatbotTraining.new_training(part1=part1, part2=part2, message_id=message.id, user_id=message.author.id,
                                           user_name=message.author.name, is_manual=True, channel_id=message.channel.id,
                                           guild_id=ctx.guild.id)

    usertrain.example_usage = """
    `{prefix}train {prefix}trigger Hi {prefix}response Hello` - Trains Hi with the response Hello
    """

    @group(invoke_without_command=True)
    @guild_only()
    @has_permissions(manage_guild=True)
    async def config(self, ctx):
        """Command group to manage where the bot learns and responds from. """
        guild = ctx.guild
        embed = discord.Embed(title=f"Info for guild: {guild.name}",
                              color=blurple)
        embed.set_thumbnail(url=guild.icon_url)
        results = await ChatbotChannel.get_by(guild_id=guild.id)
        if results:
            channels = ''
            train_channels = ''
            total_messages = 0
            total_trained = 0
            for result in results:
                total_messages += result.messages
                total_trained += result.trained_messages
                if result.train_in:
                    train_channels += ' <#{}>'.format(result.channel_id)
                if result.respond_in:
                    channels += ' <#{}>'.format(result.channel_id)
            if channels == "":
                channels = "The bot does not respond in any channels. "
            if train_channels == "":
                train_channels = "The bot does not learn from any channels. "
            embed.add_field(name='Channels to respond in: ', value=channels)
            embed.add_field(name='Channels to train in: ', value=train_channels)
            embed.add_field(name='Total messages: ', value=str(total_messages))
            embed.add_field(name='Total trained messages: ', value=str(total_trained))
            await ctx.send(embed=embed)

    config.example_usage = """
    `{prefix}config` - Show the current configuration of the guild. 
    `{prefix}config startresponding #channel` - Makes it so the bot will respond to messages in #channel. 
    `{prefix}config stopresponding #channel` - Makes it so the bot will not respond to messages in #channel. 
    `{prefix}config stoptraining #channel` - Stops the bot from learning in #channel.
    `{prefix}config starttraining #channel` - Makes it so the bot will learn from messages in #channel.
    """

    @config.command()
    @guild_only()
    @has_permissions(manage_guild=True)
    async def stoptraining(self, ctx, *, channel: discord.TextChannel = None):
        """Stop the chatbot from learning in a channel. """
        if channel is None:
            channel = ctx.channel

        db_channel = await self.load_channel(channel.id, channel.guild.id)
        embed = discord.Embed(title='Config')
        if not db_channel.train_in:
            embed.description = f"Chatbot already did not train in <#{channel.id}>"
            embed.colour = discord.Color.orange()
        else:
            db_channel.train_in = False
            db_channel.dirty = True
            await self.sync_channel(channel.id, channel.guild.id)
            embed.description = f"Chatbot will not train in <#{channel.id}>"
            embed.colour = discord.Color.green()
        await ctx.send(embed=embed)

    @config.command()
    @guild_only()
    @has_permissions(manage_guild=True)
    async def starttraining(self, ctx, *, channel: discord.TextChannel = None):
        """Make the chatbot learn in a channel. """
        if channel is None:
            channel = ctx.channel

        db_channel = await self.load_channel(channel.id, channel.guild.id)
        embed = discord.Embed(title='Config')
        if db_channel.train_in is False:
            db_channel.train_in = True
            db_channel.dirty = True
            await self.sync_channel(channel.id, channel.guild.id)
            embed.description = f'Chatbot will now train in channel <#{channel.id}>.'
            embed.colour = discord.Color.green()
        else:
            embed.description = f'Chatbot already trained in channel <#{channel.id}>.'
            embed.colour = discord.Color.orange()
        await ctx.send(embed=embed)

    @config.command()
    @guild_only()
    @has_permissions(manage_guild=True)
    async def stopresponding(self, ctx, *, channel: discord.TextChannel = None):
        """Remove a channel that the bot responds in"""
        if channel is None:
            channel = ctx.channel

        db_channel = await self.load_channel(channel.id, channel.guild.id)
        embed = discord.Embed(title='Config')
        if not db_channel.respond_in:
            embed.description = f'Chatbot already did not respond in <#{channel.id}>'
            embed.colour = discord.Color.orange()
        else:
            db_channel.respond_in = False
            db_channel.dirty = True
            await self.sync_channel(channel.id, channel.guild.id)
            embed.description = f'Chatbot will not respond in <#{channel.id}>'
            embed.colour = discord.Color.green()
        await ctx.send(embed=embed)

    @config.command()
    @guild_only()
    @has_permissions(manage_guild=True)
    async def startresponding(self, ctx, *, channel: discord.TextChannel = None):
        """Add a new channel that the bot responds in"""
        if channel is None:
            channel = ctx.channel

        db_channel = await self.load_channel(channel.id, channel.guild.id)
        embed = discord.Embed(title='Config')
        if db_channel.respond_in is False:
            db_channel.respond_in = True
            db_channel.dirty = True
            await self.sync_channel(channel.id, channel.guild.id)
            embed.description = f'Chatbot will now respond in channel <#{channel.id}>'
            embed.colour = discord.Color.green()
        else:

            embed.description = f'Chatbot already responded in channel <#{channel.id}>'
            embed.colour = discord.Color.orange()
        await ctx.send(embed=embed)

    @command()
    @dev_check()
    async def announce(self, ctx, *, message: str):
        """Used for the bot developer to make announcements about the bots functionality."""
        if message == "":
            raise UserInputError("There must be an input.")
        channels = await ChatbotChannel.get_by(respond_in=True)
        if channels:
            embed = discord.Embed(title="Announcement from the bot developer:", color=discord.Color.gold())
            embed.add_field(name="Content:", value=message)
            complete = 0
            error = 0
            for db_channel in channels:
                try:
                    channel = await ctx.bot.fetch_channel(db_channel.channel_id)
                    await channel.send(embed=embed)
                    complete += 1
                except Exception as e:
                    logger.error(e)
                    error += 1
            embed.add_field(name="Complete", value=str(complete))
            embed.add_field(name="Error", value=str(error))
            await ctx.send(embed=embed)

    @command(name="checkcache")
    @dev_check()
    async def check_cache(self, ctx):
        """Developer only command to check the cache"""
        embed = discord.Embed(title="Cache", color=blurple)
        embed.add_field(name="Channels: ", value=str(len(self._channel_cache.keys())))
        embed.add_field(name="Users: ", value=str(len(self._user_cache.keys())))
        await ctx.send(embed=embed)

    @group(invoke_without_command=True)
    @dev_check()
    async def training(self, ctx):
        """Dev only command group used to manage the bot training. """
        return

    training.example_usage = """
    `{prefix}training load` - Loads the past training from users. 
    `{prefix}training load false` - Loads only training from users that was trained using the train command. 
    `{prefix}training drop` - Deletes all bot training and reloads the cog to recreate the database tables.
    `{prefix}training corpus` - Loads the bots training from its pre-made corpus.  
    """

    @training.command()
    @dev_check()
    async def drop(self, ctx):
        """Developer only command to reset the bots training. """
        await db.Pool.execute("""DROP TABLE statement CASCADE; """)
        await db.Pool.execute("""DROP TABLE tag CASCADE; """)
        await db.Pool.execute("""DROP TABLE tag_association CASCADE; """)
        await ctx.send(embed=discord.Embed(title="Dropped training. Reloading cog.", color=discord.Color.red()))
        await self.bot.reload_extension('chatbot.cogs.chat')

    @training.command()
    @dev_check()
    async def load(self, ctx, no_automatic: bool = False):
        """Developer command to load the past training from users"""
        embed = discord.Embed(title="Loading training", color=discord.Color.orange(),
                              description='Status: Loading from sql server')
        msg = await ctx.send(embed=embed)
        i = 0
        if no_automatic:
            data = await ChatbotTraining.get_by(is_manual=True)
        else:
            data = await ChatbotTraining.get_by()
        embed.description = f"Status: Loaded {str(len(data))} statements from sql server. "
        await msg.edit(embed=embed)
        try:
            if data:
                # await asyncio.gather(*[train_process(data[i].part1, data[i].part2) for i in range(0, len(data))])
                for strings in data:
                    i += 1
                    try:
                        await self.train_process(strings.part1, strings.part2)
                    except Exception as e:
                        pass
                    if i % 20 == 0:
                        embed.description = f"Status: Trained {i} of {str(len(data))} statements. " \
                                            f"({str(round(int(100 * 100 * (i / len(data)))) / 100)}%)"
                        await msg.edit(embed=embed)
            embed.description = f"Done training. Trained {str(i)} statements"
            embed.colour = discord.Color.green()
            await msg.edit(embed=embed)
        except Exception as e:
            await msg.edit(embed=discord.Embed(title="Training corpus", description="Error. ",
                                               colour=discord.Color.red()))
            raise e

    @training.command()
    @dev_check()
    async def corpus(self, ctx):
        """Developer command to load training from the premade chatterbot corpus"""
        trainer = ChatterBotCorpusTrainer(ChatBot(
            'Fred',
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            logic_adapters=[
                'chatterbot.logic.BestMatch'
            ],
            database_uri=self.db_url
        ))
        things_to_train = [
            "chatterbot.corpus.english.ai",
            "chatterbot.corpus.english.computers",
            "chatterbot.corpus.english.conversations",
            "chatterbot.corpus.english.botprofile",
            "chatterbot.corpus.english.emotion",
            "chatterbot.corpus.english.gossip",
            "chatterbot.corpus.english.food",
            "chatterbot.corpus.english.greetings",
            "chatterbot.corpus.english.health",
            # "chatterbot.corpus.english.history",
            # "chatterbot.corpus.english.humor",
            "chatterbot.corpus.english.literature",
            "chatterbot.corpus.english.money",
            "chatterbot.corpus.english.movies",
            # "chatterbot.corpus.english.politics",
            "chatterbot.corpus.english.psychology",
            # "chatterbot.corpus.english.science",
            # "chatterbot.corpus.english.sports",
            "chatterbot.corpus.english.trivia"
            #    "chatterbot.corpus.english"
        ]
        training_status = {}
        embed = discord.Embed(title="Training corpus", color=discord.Color.orange(),
                              description=f"Training {len(things_to_train)} topics. ")
        for a in things_to_train:
            training_status[a] = "Not started"
            embed.add_field(name=a, value=training_status[a])
        msg = await ctx.send(embed=embed)
        for a in things_to_train:
            training_status[a] = "In progress"
            embed = discord.Embed(title="Training corpus", color=discord.Color.orange())
            for b in things_to_train:
                embed.add_field(name=b.split('.')[3], value=training_status[b])
            await msg.edit(embed=embed)
            try:
                trainer.train(a)
                training_status[a] = "Done."
            except Exception as e:
                capture_exception()
                training_status[a] = "Error"
                logger.error(e)

        embed = discord.Embed(title="Trained corpus", color=discord.Color.green())
        for b in things_to_train:
            embed.add_field(name=b.split('.')[3], value=training_status[b])
        await msg.edit(embed=embed)

    async def load_channel(self, channel_id, guild_id):
        """Check to see if a member is in the level cache and if not load from the database"""
        cached_channel = self._channel_cache.get(channel_id)
        if cached_channel is None:
            logger.debug("Cache miss: channel_id = %d", channel_id)
            cached_channel = await ChatbotChannelCache.from_channel_id(channel_id=channel_id, guild_id=guild_id)
            self._channel_cache[channel_id] = cached_channel
        return cached_channel

    async def load_user(self, user_id):
        """Check to see if a member is in the level cache and if not load from the database"""
        cached_user = self._user_cache.get(user_id)
        if cached_user is None:
            logger.debug("Cache miss: user_id = %d", user_id)
            cached_user = await ChatbotUserCache.from_user_id(user_id=user_id)
            self._user_cache[user_id] = cached_user
        return cached_user

    async def sync_user(self, user_id):
        """Sync an individual member to the database"""
        cached_user = self._user_cache.get(user_id)
        if cached_user:
            e = ChatbotUser(user_id=user_id, banned=cached_user.banned, messages=cached_user.messages,
                            user_name=cached_user.user_name)
            await e.update_or_add()
            cached_user.dirty = False
            return True
        else:
            return False

    async def sync_channel(self, channel_id, guild_id):
        """Sync an individual member to the database"""
        cached_channel = self._channel_cache.get(channel_id)
        if cached_channel:
            e = ChatbotChannel(channel_id=channel_id, guild_id=guild_id,
                               messages=cached_channel.messages,
                               respond_in=cached_channel.respond_in, processing=cached_channel.processing,
                               last_message=cached_channel.last_message, train_in=cached_channel.train_in,
                               trained_messages=cached_channel.trained_messages,
                               channel_name=cached_channel.channel_name)
            await e.update_or_add()
            cached_channel.dirty = False
            return True
        else:
            return False

    async def should_respond_channel(self, channel):
        """Checks if the bot should respond in the channel"""
        if channel.respond_in is True:
            return True
        return False

    async def should_respond_message(self, message, author, channel, prefix):
        """Checks if the bot should respond to that specific message."""
        if message.content.lower().startswith(prefix[2]):
            return False
        if author.banned is True:
            await message.reply('You have been banned from the chatbot for the safety of our users. ',
                                mention_author=False)
            return False
        if message.reference is not None and message.reference.message_id is not None:
            repliedto = await message.channel.fetch_message(message.reference.message_id)
            if not (repliedto.content.startswith('-') or repliedto.content == ""):
                if repliedto.author.id != self.bot.user.id:
                    return False
            else:
                return False
        # bot should not respond if processing is > rate limit
        if channel.processing >= globalratelimit:
            await message.reply('Your channel has too many messages waiting to be processed. Your input has been '
                                'ignored. ')
            return False
        else:
            channel.processing += 1

        return True

    async def should_train(self, channel, message, prefix):
        """Checks what the bot should train when given message"""
        if message.content.startswith(prefix):
            return False, "", ""
        user = await self.load_user(message.author.id)
        if user.banned:
            return False, "", ""
        if channel:
            if not channel.train_in:
                return False, "", ""
            if message.reference is not None and message.reference.message_id is not None:
                repliedto = await message.channel.fetch_message(message.reference.message_id)
                if not (repliedto.content.startswith(prefix) or repliedto.content == ""):
                    return True, repliedto.content, message.content
                else:
                    return False, "", ""
            else:
                if channel.last_message is not None:
                    return True, channel.last_message, message.content
                else:
                    return False, "", ""
        else:
            return False, "", ""

    @group(name='chattrigger', invoke_without_command=True)
    @guild_only()
    async def trigger(self, ctx):
        """Command group to manage bot triggers."""
        results = await ChatbotCustom.get_by(guild_id=ctx.guild.id)
        if not results:
            embed = discord.Embed(title="Triggers for {}".format(ctx.guild.name))
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.description = "No triggers found for this guild! Add one using `{}trigger add <regex> [user]`".format(
                ctx.prefix)
            embed.colour = discord.Color.red()
            await ctx.send(embed=embed)
            return
        for result in results:
            if result.user_id == 1:
                result.user_id = "All users."
            else:
                result.user_id = f"<@{result.user_id}>"
        fmt = 'ID {0.id}: `{0.regex}`, {0.user_id}'

        filter_text = '\n'.join(map(fmt.format, results))
        embed = discord.Embed(title=f"Triggers for {ctx.guild.name}")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        if len(filter_text) > 1024:
            embed.description = filter_text
        else:
            embed.add_field(name="Triggers", value=filter_text)
        embed.colour = discord.Color.dark_orange()
        await ctx.send(embed=embed)

    trigger.example_usage = """
    `{prefix}trigger add test @Fred` - Makes it so the bot will respond when Fred says test.
    `{prefix}trigger` - List all the triggers in the guild. 
    `{prefix}trigger remove 15` - Removes the trigger with the id 15. 
    """

    @guild_only()
    @trigger.command()
    @has_permissions(manage_messages=True)
    async def add(self, ctx, regex, user: discord.Member = None):
        """Adds a trigger that the bot will respond to"""
        if user:
            if user.bot:
                await ctx.send(embed=discord.Embed(title="You cannot add filters for a bot.",
                                                   color=discord.Color.red()))
                return
            already_existing_triggers = await ChatbotCustom.get_by(regex=regex.lower(), user_id=user.id,
                                                                   guild_id=ctx.guild.id)
            if len(already_existing_triggers) > 0:
                await ctx.send(embed=discord.Embed(title="Trigger already exists", colour=discord.Color.red()))
                return
            new = ChatbotCustom(guild_id=ctx.guild.id, user_id=user.id, regex=regex.lower())
            await new.update_or_add()
            await ctx.send(embed=discord.Embed(title=f"Trigger {regex} added for user {user.display_name}.",
                                               color=discord.Color.green()))
        else:
            already_existing_triggers = await ChatbotCustom.get_by(regex=regex.lower(), user_id=1,
                                                                   guild_id=ctx.guild.id)
            if len(already_existing_triggers) > 0:
                await ctx.send(embed=discord.Embed(title="Trigger already exists", colour=discord.Color.red()))
                return
            new = ChatbotCustom(guild_id=ctx.guild.id, user_id=1, regex=regex.lower())
            await new.update_or_add()
            await ctx.send(embed=discord.Embed(title=f"Trigger {regex} added for all users.",
                                               color=discord.Color.green()))

    @guild_only()
    @trigger.command()
    @has_permissions(manage_messages=True)
    async def remove(self, ctx, trigger_id: int):
        """Removes a trigger that the bot responds to."""
        triggers = await ChatbotCustom.get_by(guild_id=ctx.guild.id, id=trigger_id)
        if not triggers:
            await ctx.send(embed=discord.Embed(title="There are no triggers in this guild with that id. "),
                           color=discord.Color.red())
        else:
            trigger = triggers[0]
            embed = discord.Embed(title="Trigger deleted.", color=discord.Color.red())
            if trigger.user_id == 1:
                embed.description = f"ID: {trigger.id}, Target: <@{trigger.user_id}>, Trigger: {trigger.regex}"
            else:
                embed.description = f"ID: {trigger.id}, Target: All users, Trigger: {trigger.regex}"
            await ctx.send(embed=embed)
            await ChatbotCustom.delete(id=trigger_id, guild_id=ctx.guild.id)

    async def should_respond_custom(self, message):
        """Evaluates whether any custom triggers have been triggered by this message. """
        user = await self.load_user(message.author.id)
        if message.content.startswith("-") or message.author.bot or user.banned:
            return False
        results = await ChatbotCustom.get_by(guild_id=message.guild.id, user_id=message.author.id)
        results.extend(await ChatbotCustom.get_by(guild_id=message.guild.id, user_id=1))
        if results is None:
            print("results is none")
            return False
        else:
            for result in results:
                if result.regex.lower() in message.content.lower():
                    return True
        return False

    @Cog.listener('on_message')
    @guild_only()
    async def respond_to_message(self, message):
        """Check if message channel is valid and if so respond in it."""
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel):
            return

        ctx: LilyBotContext = await self.bot.get_context(message)
        if message.content.lower().startswith(ctx.prefix):
            return
        author = await self.load_user(message.author.id)
        channel = await self.load_channel(message.channel.id, message.channel.guild.id)
        if channel.channel_name != message.channel.name:
            channel.channel_name = message.channel.name
            channel.dirty = True

        to_train, part1, part2 = await self.should_train(channel, message, ctx.prefix)
        part1 = clean(ctx, part1)
        part2 = clean(ctx, part2)

        if author.user_name != message.author.name:
            author.user_name = message.author.name
            author.dirty = True

        if await self.should_respond_channel(channel):
            if await self.should_respond_message(message, author, channel, ctx.prefix):
                async with ctx.typing():
                    user_content = clean(ctx, message.content)
                    if message.attachments:
                        for attachment in message.attachments:
                            url = attachment.url
                            user_content = user_content + '\n' + url
                    result = await self.respond_process(user_content)
                    if result == "":
                        result = await self.respond_process(user_content)
                        if result == "":
                            result = "There was a problem processing your input."
                    try:
                        if self.next_responses[ctx.guild.id] is not None:
                            result = self.next_responses[ctx.guild.id]
                            self.next_responses[ctx.guild.id] = None
                    except KeyError:
                        pass
                    channel.processing -= 1
                    if result == "There was a problem processing your input.":
                        embed = discord.Embed(title="Error", description="There was a problem processing your input.",
                                              color=discord.Color.red())
                        await ctx.reply(embed=embed, mention_author=False)
                    else:
                        await ctx.reply(clean(ctx, result.replace("/n", "\n")), mention_author=False)

                if not result.startswith("There was a problem processing your input."):
                    channel.last_message = result
                    channel.messages += 1
                    author.messages += 1
                    author.dirty = True
        elif await self.should_respond_custom(message):
            channel.messages += 1
            channel.dirty = True
            author.messages += 1
            author.dirty = True
            async with ctx.typing():
                result = await self.respond_process(message.content)
                await ctx.reply(clean(ctx, result.replace("/n", "\n")), mention_author=False)
            return
        if to_train is True:
            await self.train_process(part1, part2)
            await ChatbotTraining.new_training(part1=part1, part2=part2, is_manual=False, message_id=message.id,
                                               user_id=message.author.id, user_name=message.author.name,
                                               channel_id=ctx.channel.id, guild_id=ctx.guild.id)
            channel.trained_messages += 1
            channel.dirty = True
        await self.sync_user(message.author.id)
        await self.sync_channel(channel_id=message.channel.id, guild_id=message.guild.id)

    async def preloadcache(self):
        """Preloads all users and channels into the cache. """
        results = await ChatbotChannel.get_by()
        if results:
            for result in results:
                await self.load_channel(result.channel_id, result.guild_id)
        results = await ChatbotUser.get_by()
        if results:
            for result in results:
                await self.load_user(result.user_id)

    @loop(minutes=2.5)
    async def sync_task(self):
        """Sync dirty records to the database, and evict others from the cache.
        This function merely wraps `sync_to_database` into a periodic task.
        """
        # @loop(...) assumes that getattr(self, func.__name__) is the task, so this needs to be a new function instead
        # of `sync_task = loop(minutes=1)(sync_to_database)`

        await self.sync_channels_to_database()
        await self.sync_users_to_database()

    @sync_task.before_loop
    async def before_sync(self):
        """Do preparation work before starting the periodic timer to sync cache with the database."""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        """Detach from the running bot and cancel long-running code as the cog is unloaded."""
        self.sync_task.stop()

    @command()
    @dev_check()
    async def syncdb(self, ctx):
        """Developer command to force a database sync"""
        await self.sync_channels_to_database()
        await self.sync_users_to_database()

        await ctx.send(embed=discord.Embed(title="Done syncing.", color=discord.Color.green()))

    async def sync_users_to_database(self):
        """Sync dirty records to the database, and evict others from the cache."""

        # Deleting from a dict while iterating will error, so collect the keys up front and iterate that
        # Note that all mutation of `self._xp_cache` happens before the first yield point to prevent race conditions
        keys = list(self._user_cache.keys())
        to_write = []  # records to write to the database
        evicted = 0
        for user_id in keys:
            cached_user = self._user_cache[user_id]
            if not cached_user.dirty:
                # Evict records that haven't changed since last run from cache to conserve memory
                del self._user_cache[user_id]
                evicted += 1
                continue
            to_write.append((user_id, cached_user.banned,
                             cached_user.messages, cached_user.user_name))
            cached_user.dirty = False

        if not to_write:
            logger.debug("Sync task skipped, nothing to do")
            return
        # Query written manually to insert all records at once
        try:
            async with db.Pool.acquire() as conn:
                await conn.executemany(
                    f"INSERT INTO {ChatbotUser.__tablename__} (user_id, banned, messages, user_name) "
                    f" VALUES ($1, $2, $3, $4) ON CONFLICT ({ChatbotUser.__uniques__}) DO UPDATE "
                    f" SET banned = EXCLUDED.banned, messages = EXCLUDED.messages, "
                    f"user_name = EXCLUDED.user_name;",
                    to_write)
            logger.debug(
                f"Inserted/updated {len(to_write)} record(s); Evicted {evicted} records(s)")
        except Exception as e:
            logger.error(
                f"Failed to sync user cache to db, Reason:{e}")

    async def sync_channels_to_database(self):
        """Sync dirty records to the database, and evict others from the cache."""

        # Deleting from a dict while iterating will error, so collect the keys up front and iterate that
        # Note that all mutation of `self._xp_cache` happens before the first yield point to prevent race conditions
        keys = list(self._channel_cache.keys())
        to_write = []  # records to write to the database
        evicted = 0
        for channel_id in keys:
            cached_channel = self._channel_cache[channel_id]

            if not cached_channel.dirty:
                # Evict records that haven't changed since last run from cache to conserve memory
                del self._channel_cache[channel_id]
                evicted += 1
                continue
            to_write.append((channel_id, cached_channel.guild_id, cached_channel.messages, cached_channel.respond_in,
                             cached_channel.last_message, 0, cached_channel.train_in, cached_channel.trained_messages,
                             cached_channel.channel_name))
            cached_channel.dirty = False

        if not to_write:
            logger.debug("Sync task skipped, nothing to do")
            return
        # Query written manually to insert all records at once
        try:
            async with db.Pool.acquire() as conn:
                await conn.executemany(f"INSERT INTO {ChatbotChannel.__tablename__} (channel_id, guild_id, messages, "
                                       f"respond_in, last_message, processing, train_in, trained_messages, "
                                       f"channel_name) "
                                       f" VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                                       f"ON CONFLICT ({ChatbotChannel.__uniques__}) DO UPDATE "
                                       f" SET messages = EXCLUDED.messages, respond_in = EXCLUDED.respond_in, "
                                       f"last_message = EXCLUDED.last_message, "
                                       f"processing = EXCLUDED.processing, train_in = EXCLUDED.train_in, "
                                       f"trained_messages = EXCLUDED.trained_messages, channel_name = "
                                       f"EXCLUDED.channel_name;",
                                       to_write)
            logger.debug(
                f"Inserted/updated {len(to_write)} record(s); Evicted {evicted} records(s)")
        except Exception as e:
            logger.error(
                f"Failed to sync channels cache to db, Reason:{e}")


async def setup(bot):
    """Add the levels cog to a bot."""
    await bot.add_cog(Chat(bot))
