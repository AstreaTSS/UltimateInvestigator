"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import asyncio
import importlib
import os
import platform
import subprocess
import time
from importlib.metadata import version as _v

import interactions as ipy
import tansy

import common.utils as utils

IPY_VERSION = _v("discord-py-interactions")
PYTHON_VERSION = platform.python_version_tuple()
PYTHON_IMPLEMENTATION = platform.python_implementation()


class OtherCMDs(utils.Extension):
    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "General"
        self.bot: utils.THIABase = bot
        self.invite_link = ""

        self.bot.create_task(self.when_ready())

    async def when_ready(self) -> None:
        await self.bot.wait_until_ready()
        self.invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=532576332864&scope=bot%20applications.commands"

    def _get_commit_hash(self) -> str | None:
        try:
            return (
                subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
                .decode("ascii")
                .strip()
            )
        except Exception:  # screw it
            return None

    async def get_commit_hash(self) -> str | None:
        return await asyncio.to_thread(self._get_commit_hash)

    @tansy.slash_command(
        "ping",
        description=(
            "Pings the bot. Great way of finding out if the bot's working correctly,"
            " but has no real use."
        ),
    )
    async def ping(self, ctx: utils.THIASlashContext) -> None:
        start_time = time.perf_counter()
        average_ping = round((self.bot.latency * 1000), 2)

        embed = ipy.Embed(
            "Pong!", color=self.bot.color, timestamp=ipy.Timestamp.utcnow()
        )
        embed.description = f"Discord Ping: `{average_ping}` ms\nCalculating RTT..."

        mes = await ctx.send(embed=embed)

        end_time = time.perf_counter()
        # not really rtt ping but shh
        rtt_ping = round(((end_time - start_time) * 1000), 2)
        embed.description = (
            f"Discord Ping: `{average_ping}` ms\nRTT Ping: `{rtt_ping}` ms"
        )

        await ctx.edit(message=mes, embed=embed)

    @ipy.slash_command(
        name="invite",
        description="Sends instructions on how to set up and invite the bot.",
    )
    async def invite(self, ctx: utils.THIASlashContext) -> None:
        embed = utils.make_embed(
            "If you want to invite me to your server, it's a good idea to use the"
            " Server Setup Guide. However, if you know what you're doing, you can"
            " use the Invite Link instead.",
            title="Invite Bot",
        )
        components = [
            ipy.Button(
                style=ipy.ButtonStyle.URL,
                label="Server Setup Guide",
                url="https://pythia.astrea.cc/server_setup.html",
            ),
            ipy.Button(
                style=ipy.ButtonStyle.URL,
                label="Invite Link",
                url=self.invite_link,
            ),
        ]
        await ctx.send(embeds=embed, components=components)

    @ipy.slash_command(
        "support", description="Gives an invite link to the support server."
    )
    async def support(self, ctx: utils.THIASlashContext) -> None:
        embed = utils.make_embed(
            "If you need help with the bot, or just want to hang out, join the"
            " support server!",
            title="Support Server",
        )
        button = ipy.Button(
            style=ipy.ButtonStyle.URL,
            label="Join Support Server",
            url="https://discord.gg/NSdetwGjpK",
        )
        await ctx.send(embeds=embed, components=button)

    @tansy.slash_command("about", description="Gives information about the bot.")
    async def about(self, ctx: ipy.THIASlashContext) -> None:
        msg_list = [
            (
                '> "Hello. I am PYTHIA, the Ultimate Robotic Assistant. I look forward'
                ' to assisting you in whatever tasks you may have."'
            ),
            (
                (
                    "PYTHIA is a Discord bot meant to assist with Danganronpa/Killing"
                    " Game RPs. Currently, it automates parts of investigating that"
                    " would otherwise take time and energy to make it easier to run"
                    " RPs. More specifically, it allows for staff to define 'key"
                    " phrases'/triggers that players can later activate through the"
                    " bot."
                ),
                (
                    "The bot is planned to increase in scope, adding featues like a"
                    " gacha system in the future."
                ),
            ),
        ]

        about_embed = ipy.Embed(
            title="About",
            color=self.bot.color,
            description="\n".join(msg_list),
        )
        about_embed.set_thumbnail(
            ctx.guild.me.display_avatar.url
            if ctx.guild
            else self.bot.user.display_avatar.url
        )

        commit_hash = await self.get_commit_hash()
        command_num = len(self.bot.application_commands) + len(
            self.bot.prefixed.commands
        )

        about_embed.add_field(
            name="Stats",
            value="\n".join(
                (
                    f"Servers: {self.bot.guild_count}",
                    f"Commands: {command_num} ",
                    (
                        "Startup Time:"
                        f" {ipy.Timestamp.fromdatetime(self.bot.start_time).format(ipy.TimestampStyles.RelativeTime)}"
                    ),
                    (
                        "Commit Hash:"
                        f" [{commit_hash}](https://github.com/AstreaTSS/PYTHIA/commit/{commit_hash})"
                        if commit_hash
                        else "Commit Hash: N/A"
                    ),
                    (
                        "Interactions.py Version:"
                        f" [{IPY_VERSION}](https://github.com/interactions-py/interactions.py/tree/{IPY_VERSION})"
                    ),
                    (
                        "Python Version:"
                        f" {PYTHON_IMPLEMENTATION} {PYTHON_VERSION[0]}.{PYTHON_VERSION[1]}"
                    ),
                    "Made By: [AstreaTSS](https://astrea.cc)",
                )
            ),
            inline=True,
        )

        links = [
            "Website: [Link](https://pythia.astrea.cc)",
            f"Invite Bot: [Link]({self.invite_link})",
            "Support Server: [Link](https://discord.gg/NSdetwGjpK)",
        ]

        if os.environ.get("TOP_GG_TOKEN"):
            links.append(f"Top.gg Page: [Link](https://top.gg/bot/{self.bot.user.id})")

        links.extend(
            (
                "Source Code: [Link](https://github.com/AstreaTSS/PYTHIA)",
                "Terms of Service: [Link](https://pythia.astrea.cc/legal/tos.html)",
                (
                    "Privacy Policy:"
                    " [Link](https://pythia.astrea.cc/legal/privacy_policy.html)"
                ),
            )
        )

        about_embed.add_field(
            name="Links",
            value="\n".join(links),
            inline=True,
        )
        about_embed.timestamp = ipy.Timestamp.utcnow()

        await ctx.send(embed=about_embed)


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    OtherCMDs(bot)
