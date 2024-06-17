"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import importlib

import interactions as ipy
import tansy
import typing_extensions as typing

import common.utils as utils


class ConfigCMDs(utils.Extension):
    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "Config"
        self.bot: utils.THIABase = bot

    config = tansy.SlashCommand(
        name="config",
        description="Handles configuration of general bot settings.",
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
        dm_permission=False,
    )

    @config.subcommand(
        sub_cmd_name="info",
        sub_cmd_description=(
            "Lists out the general configuration settings for the server."
        ),
    )
    async def general_config(self, ctx: utils.THIASlashContext) -> None:
        config = await ctx.fetch_config()

        only_option_rn = (
            "Player role:"
            f" {f'<@&{config.player_role}>' if config.player_role else 'N/A'}\n\n*Looking"
            " a bit empty? This is the general configuration display - check out the"
            " other config commands for more of your configuration.*"
        )
        await ctx.send(
            embed=utils.make_embed(only_option_rn, title="General Configuration")
        )

    @config.subcommand(
        sub_cmd_name="player",
        sub_cmd_description="Sets (or unsets) the Player role.",
    )
    async def set_player_role(
        self,
        ctx: utils.THIASlashContext,
        role: typing.Optional[ipy.Role] = tansy.Option(
            "The Player role to use.",
            default=None,
        ),
        unset: bool = tansy.Option("Should the role be unset?", default=False),
    ) -> None:
        if not (bool(role) ^ unset):
            raise ipy.errors.BadArgument(
                "You must either specify a role or specify to unset the role."
            )

        guild_config = await ctx.fetch_config()
        guild_config.player_role = role.id if role else None
        await guild_config.save()

        if role:
            await ctx.send(
                embed=utils.make_embed(f"Player role set to {role.mention}!"),
            )
        else:
            await ctx.send(embed=utils.make_embed("Player role unset."))

    @config.subcommand(
        sub_cmd_name="help",
        sub_cmd_description="Tells you how to set up this bot.",
    )
    async def setup_help(
        self,
        ctx: utils.THIASlashContext,
    ) -> None:
        embed = utils.make_embed(
            "To set up this bot, follow the Server Setup Guides below.",
            title="Setup Bot",
        )
        button = ipy.Button(
            style=ipy.ButtonStyle.LINK,
            label="Server Setup Guide",
            url="https://pythia.astrea.cc/setup/index.html",
        )
        await ctx.send(embeds=embed, components=button)


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    ConfigCMDs(bot)
