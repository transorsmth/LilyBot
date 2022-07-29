"""Context for LilyBot message to clean messages before sending"""
import discord
from discord.ext import commands

from lilybot import utils


class LilyBotContext(commands.Context):
    """Cleans all messages before sending"""

    async def send(self, content: str = None, **kwargs):  # pylint: disable=arguments-differ
        if content is not None:
            content = utils.clean(self, content, mass=True,
                                  member=False, role=False, channel=False)

        return await super().send(content, **kwargs)

    async def reply(self, content: str = None, **kwargs):
        if content is not None:
            content = utils.clean(self, content, mass=True,
                                  member=False, role=False, channel=False)
        try:
            result = await super().reply(content, **kwargs)
        except discord.HTTPException:
            result = await super().send(content, **kwargs)
        return result
