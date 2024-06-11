"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import asyncio
import contextlib
import importlib
import io
import platform
import textwrap
import traceback
import typing

import interactions as ipy
from interactions.ext import paginators
from interactions.ext import prefixed_commands as prefixed
from interactions.ext.debug_extension.utils import debug_embed, get_cache_state

import common.utils as utils


class OwnerCMDs(ipy.Extension):
    def __init__(self, bot: utils.THIABase) -> None:
        self.bot: utils.THIABase = bot
        self.name = "Owner"

        self.set_extension_error(self.ext_error)
        self.add_ext_check(ipy.is_owner())

    @prefixed.prefixed_command(aliases=["jsk"])
    async def debug(self, ctx: prefixed.PrefixedContext) -> None:
        """Get basic information about the bot."""
        uptime = ipy.Timestamp.fromdatetime(self.bot.start_time)
        e = debug_embed("General")
        e.set_thumbnail(self.bot.user.avatar.url)
        e.add_field("Operating System", platform.platform())

        e.add_field(
            "Version Info",
            f"interactions.py@{ipy.__version__} | Py@{ipy.__py_version__}",
        )

        e.add_field("Start Time", f"{uptime.format(ipy.TimestampStyles.RelativeTime)}")

        if privileged_intents := [
            i.name for i in self.bot.intents if i in ipy.Intents.PRIVILEGED
        ]:
            e.add_field("Privileged Intents", " | ".join(privileged_intents))

        e.add_field("Loaded Extensions", ", ".join(self.bot.ext))

        e.add_field("Guilds", str(self.bot.guild_count))

        await ctx.reply(embeds=[e])

    @debug.subcommand(aliases=["cache"])
    async def cache_info(self, ctx: prefixed.PrefixedContext) -> None:
        """Get information about the current cache state."""
        e = debug_embed("Cache")

        e.description = f"```prolog\n{get_cache_state(self.bot)}\n```"
        await ctx.reply(embeds=[e])

    @debug.subcommand()
    async def shutdown(self, ctx: prefixed.PrefixedContext) -> None:
        """Shuts down the bot."""
        await ctx.reply("Shutting down 😴")
        await self.bot.stop()

    @debug.subcommand()
    async def reload(self, ctx: prefixed.PrefixedContext, *, module: str) -> None:
        """Regrows an extension."""
        self.bot.reload_extension(module)
        await ctx.reply(f"Reloaded `{module}`.")

    @debug.subcommand()
    async def load(self, ctx: prefixed.PrefixedContext, *, module: str) -> None:
        """Grows a scale."""
        self.bot.load_extension(module)
        await ctx.reply(f"Loaded `{module}`.")

    @debug.subcommand()
    async def unload(self, ctx: prefixed.PrefixedContext, *, module: str) -> None:
        """Sheds a scale."""
        self.bot.unload_extension(module)
        await ctx.reply(f"Unloaded `{module}`.")

    @prefixed.prefixed_command(aliases=["reloadallextensions"])
    async def reload_all_extensions(self, ctx: prefixed.PrefixedContext) -> None:
        for ext in (e.extension_name for e in self.bot.ext.copy().values()):
            self.bot.reload_extension(ext)
        await ctx.reply("All extensions reloaded!")

    @reload.error
    @load.error
    @unload.error
    async def extension_error(
        self, error: Exception, ctx: prefixed.PrefixedContext, *_: typing.Any
    ) -> ipy.Message | None:
        if isinstance(error, ipy.errors.CommandCheckFailure):
            return await ctx.reply(
                "You do not have permission to execute this command."
            )
        await utils.error_handle(error, ctx=ctx)
        return None

    @debug.subcommand(aliases=["python", "exc"])
    async def exec(self, ctx: prefixed.PrefixedContext, *, body: str) -> ipy.Message:
        """Direct evaluation of Python code."""
        await ctx.channel.trigger_typing()
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "server": ctx.guild,
            "guild": ctx.guild,
            "message": ctx.message,
        } | globals()

        body = (
            "\n".join(body.split("\n")[1:-1])
            if body.startswith("```") and body.endswith("```")
            else body.strip("` \n")
        )

        stdout = io.StringIO()

        to_compile = f"async def func():\n{textwrap.indent(body, ' ')}"
        try:
            exec(to_compile, env)  # noqa: S102
        except SyntaxError:
            return await ctx.reply(f"```py\n{traceback.format_exc()}\n```")

        func = env["func"]
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            await ctx.message.add_reaction("❌")
            raise
        else:
            return await self.handle_exec_result(ctx, ret, stdout.getvalue())

    async def handle_exec_result(
        self, ctx: prefixed.PrefixedContext, result: typing.Any, value: typing.Any
    ) -> ipy.Message:
        if result is None:
            result = value or "No Output!"

        await ctx.message.add_reaction("✅")

        if isinstance(result, ipy.Message):
            try:
                e = debug_embed(
                    "Exec", timestamp=result.created_at, url=result.jump_url
                )
                e.description = result.content
                e.set_author(
                    result.author.tag,
                    icon_url=result.author.display_avatar.url,
                )
                e.add_field(
                    "\u200b", f"[Jump To]({result.jump_url})\n{result.channel.mention}"
                )

                return await ctx.message.reply(embeds=e)
            except Exception:
                return await ctx.message.reply(result.jump_url)

        if isinstance(result, ipy.Embed):
            return await ctx.message.reply(embeds=result)

        if isinstance(result, ipy.File):
            return await ctx.message.reply(file=result)

        if isinstance(result, paginators.Paginator):
            return await result.reply(ctx)

        if hasattr(result, "__iter__"):
            l_result = list(result)
            if all(isinstance(r, ipy.Embed) for r in result):
                paginator = paginators.Paginator.create_from_embeds(self.bot, *l_result)
                return await paginator.reply(ctx)

        if not isinstance(result, str):
            result = repr(result)

        # prevent token leak
        result = result.replace(self.bot.http.token, "[REDACTED TOKEN]")

        if len(result) <= 2000:
            return await ctx.message.reply(f"```py\n{result}```")

        paginator = paginators.Paginator.create_from_string(
            self.bot, result, prefix="```py", suffix="```", page_size=4000
        )
        return await paginator.reply(ctx)

    @debug.subcommand()
    async def shell(self, ctx: prefixed.PrefixedContext, *, cmd: str) -> ipy.Message:
        """Executes statements in the system shell."""
        async with ctx.channel.typing:
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )

            output, _ = await process.communicate()
            output_str = output.decode("utf-8")
            output_str += f"\nReturn code {process.returncode}"

        if len(output_str) <= 2000:
            return await ctx.message.reply(f"```sh\n{output_str}```")

        paginator = paginators.Paginator.create_from_string(
            self.bot, output_str, prefix="```sh", suffix="```", page_size=4000
        )
        return await paginator.reply(ctx)

    @debug.subcommand()
    async def git(
        self, ctx: prefixed.PrefixedContext, *, cmd: typing.Optional[str] = None
    ) -> None:
        """Shortcut for 'debug shell git'. Invokes the system shell."""
        await self.shell.callback(ctx, cmd=f"git {cmd}" if cmd else "git")

    @debug.subcommand()
    async def pip(
        self, ctx: prefixed.PrefixedContext, *, cmd: typing.Optional[str] = None
    ) -> None:
        """Shortcut for 'debug shell pip'. Invokes the system shell."""
        await self.shell.callback(ctx, cmd=f"pip {cmd}" if cmd else "pip")

    @debug.subcommand(aliases=["sync-interactions", "sync-cmds", "sync_cmds", "sync"])
    async def sync_interactions(
        self, ctx: prefixed.PrefixedContext, scope: int = 0
    ) -> None:
        """
        Synchronizes all interaction commands with Discord.

        Should not be used lightly.
        """
        # syncing interactions in inherently intensive and
        # has a high risk of running into the ratelimit
        # while this is fine for a small bot where it's unlikely
        # to even matter, for big bots, running into this ratelimit
        # can cause havoc on other functions

        # we only sync to the global scope to make delete_commands
        # a lot better in the ratelimiting department, but i
        # would still advise caution to any self-hosters, and would
        # only suggest using this when necessary

        async with ctx.channel.typing:
            await self.bot.synchronise_interactions(
                scopes=[scope], delete_commands=True
            )

        await ctx.reply("Done!")

    async def ext_error(
        self,
        error: Exception,
        ctx: ipy.BaseContext,
        *_: typing.Any,
        **__: typing.Any,
    ) -> None:
        if isinstance(ctx, prefixed.PrefixedContext):
            ctx.send = ctx.message.reply  # type: ignore

        if isinstance(error, ipy.errors.CommandCheckFailure):
            if hasattr(ctx, "send"):
                await ctx.send("Nice try.")
            return

        error_str = utils.error_format(error)
        chunks = utils.line_split(error_str)

        for i in range(len(chunks)):
            chunks[i][0] = f"```py\n{chunks[i][0]}"
            chunks[i][len(chunks[i]) - 1] += "\n```"

        final_chunks = ["\n".join(chunk) for chunk in chunks]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks

        await utils.msg_to_owner(self.bot, to_send)

        if hasattr(ctx, "send"):
            await ctx.send("An error occured. Please check your DMs.")


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    OwnerCMDs(bot)
