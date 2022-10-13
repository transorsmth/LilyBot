"""Context for LilyBot message to clean messages before sending"""
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from lilybot import utils

if TYPE_CHECKING:
    from lilybot import LilyBot


class LilyBotContext(commands.Context):
    """Cleans all messages before sending"""
    bot: "LilyBot"

    async def send(self, content: str = None, **kwargs) -> discord.Message:  # pylint: disable=arguments-differ
        if content is not None:
            content = utils.clean(self, content, mass=True,
                                  member=False, role=False, channel=False)

        return await super().send(content, **kwargs)

    async def reply(self, content: str = None, **kwargs) -> discord.Message:
        if content is not None:
            content = utils.clean(self, content, mass=True,
                                  member=False, role=False, channel=False)
        try:
            result = await super().reply(content, **kwargs)
        except discord.HTTPException:
            result = await super().send(content, **kwargs)
        return result
