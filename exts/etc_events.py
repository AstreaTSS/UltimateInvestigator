"""
Copyright 2021-2024 AstreaTSS.
This file is part of Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import importlib

import interactions as ipy

import common.models as models
import common.utils as utils


class EtcEvents(ipy.Extension):
    def __init__(self, bot: utils.UIBase) -> None:
        self.bot: utils.UIBase = bot

    @ipy.listen("guild_join")
    async def on_guild_join(self, event: ipy.events.GuildJoin) -> None:
        if not self.bot.is_ready:
            return

        _ = await models.Config.get_or_none(
            guild_id=int(event.guild_id)
        ) or await models.Config.prisma().create(data={"guild_id": int(event.guild_id)})

    @ipy.listen("guild_left")
    async def on_guild_left(self, event: ipy.events.GuildLeft) -> None:
        if not self.bot.is_ready:
            return

        await models.Config.prisma().delete(where={"guild_id": int(event.guild_id)})


def setup(bot: utils.UIBase) -> None:
    importlib.reload(utils)
    EtcEvents(bot)
