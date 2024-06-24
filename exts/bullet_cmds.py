"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import collections
import importlib

import interactions as ipy
import tansy

import common.fuzzy as fuzzy
import common.help_tools as help_tools
import common.models as models
import common.utils as utils


def name_shorten(name: str, shorten_amount: int = 16) -> str:
    return f"{name[:shorten_amount].strip()}..." if len(name) > shorten_amount else name


def convert_to_bool(argument: str) -> bool:
    lowered = argument.lower()
    if lowered in {"yes", "y", "true", "t", "1", "enable", "on"}:
        return True
    if lowered in {"no", "n", "false", "f", "0", "disable", "off"}:
        return False
    raise ipy.errors.BadArgument(f"{argument} is not a recognised boolean option.")


class BulletCMDs(utils.Extension):
    """Commands for using and modifying Truth Bullets."""

    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "Bullet"
        self.bot: utils.THIABase = bot

    config = tansy.SlashCommand(
        name="bullet-manage",
        description="Handles management of Truth Bullets.",
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
        dm_permission=False,
    )

    @config.subcommand(
        sub_cmd_name="add",
        sub_cmd_description=(
            "Open a prompt to add Truth Bullets to a specified channel."
        ),
    )
    async def add_bullets(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel for the Truth Bullets to be added.",
            converter=utils.ValidChannelConverter,
        ),
    ) -> None:
        button = ipy.Button(
            style=ipy.ButtonStyle.GREEN,
            label=f"Add Truth Bullets for #{channel.name}",
            custom_id=f"ui-button:add_bullets-{channel.id}",
        )

        embeds: list[ipy.Embed] = []

        if (
            await models.TruthBullet.prisma().count(where={"guild_id": ctx.guild_id})
            > 0
            and await models.TruthBullet.prisma().count(
                where={"guild_id": ctx.guild_id, "found": False}
            )
            == 0
        ):
            embeds.append(
                ipy.Embed(
                    "Warning",
                    "This server has Truth Bullets that all have been found, likely"
                    " from a previous investigation. If you want to start fresh with"
                    " completely new Truth Bullets, you can clear the current ones"
                    f" with {self.bot.mention_command('clear-bullets')}.",
                    color=ipy.RoleColors.YELLOW,
                )
            )

        embeds.append(utils.make_embed("Add Truth Bullets via the button below!"))

        await ctx.send(
            embeds=embeds,
            components=button,
        )

    @ipy.listen("component")
    async def on_add_bullets_button(self, event: ipy.events.Component) -> None:
        ctx = event.ctx

        if ctx.custom_id.startswith("ui-button:add_bullets-"):
            channel_id = int(ctx.custom_id.removeprefix("ui-button:add_bullets-"))
            channel = await self.bot.fetch_channel(channel_id)

            if not channel:
                raise utils.CustomCheckFailure(
                    "Could not find the channel this was associated to. Was it deleted?"
                )

            modal = ipy.Modal(
                ipy.ShortText(
                    label="What's the trigger for this Truth Bullet?",
                    custom_id="truth_bullet_trigger",
                    max_length=60,
                ),
                ipy.ShortText(
                    label="Hide this Truth Bullet only to the finder?",
                    custom_id="truth_bullet_hidden",
                    value="no",
                    max_length=10,
                ),
                ipy.ParagraphText(
                    label="What's the description for this Truth Bullet?",
                    custom_id="truth_bullet_desc",
                    max_length=3900,
                ),
                title=f"Add Truth Bullets for #{name_shorten(channel.name)}",
                custom_id=f"ui-modal:add_bullets-{channel.id}",
            )
            await ctx.send_modal(modal)

    @ipy.listen("modal_completion")
    async def on_modal_add_bullet(self, event: ipy.events.ModalCompletion) -> None:
        ctx = event.ctx

        if ctx.custom_id.startswith("ui-modal:add_bullets-"):
            channel_id = int(ctx.custom_id.removeprefix("ui-modal:add_bullets-"))

            if await models.TruthBullet.validate(
                channel_id, ctx.responses["truth_bullet_trigger"]
            ):
                await ctx.send(
                    embed=utils.error_embed_generate(
                        f"A Truth Bullet in <#{channel_id}> already has the trigger"
                        f" `{ctx.responses['truth_bullet_trigger']}` or has an alias"
                        " named that!"
                    )
                )
                return

            try:
                hidden = convert_to_bool(ctx.responses["truth_bullet_hidden"])
            except ipy.errors.BadArgument:
                await ctx.send(
                    embed=utils.error_embed_generate(
                        "Invalid value for hiding the Truth Bullet! Giving a simple"
                        " 'yes' or 'no' will work."
                    )
                )
                return

            await models.TruthBullet.prisma().create(
                data={
                    "trigger": ctx.responses["truth_bullet_trigger"],
                    "aliases": [],
                    "description": ctx.responses["truth_bullet_desc"],
                    "channel_id": channel_id,
                    "guild_id": ctx.guild_id,
                    "found": False,
                    "finder": None,
                    "hidden": hidden,
                }
            )

            await ctx.send(
                embed=utils.make_embed(
                    "Added Truth Bullet with trigger"
                    f" `{ctx.responses['truth_bullet_trigger']}` to <#{channel_id}>!"
                ),
            )

    @config.subcommand(
        "remove",
        sub_cmd_description="Removes a Truth Bullet from the list of Truth Bullets.",
    )
    async def remove_bullet(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel for the Truth Bullet to be removed."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to be removed.", autocomplete=True
        ),
    ) -> None:
        num_deleted = await models.TruthBullet.prisma().delete_many(
            where={
                "channel_id": channel.id,
                "trigger": {
                    "equals": models.escape_ilike(trigger),
                    "mode": "insensitive",
                },
            }
        )

        if num_deleted > 0:
            await ctx.send(
                embed=utils.make_embed(
                    f"Truth Bullet with trigger `{trigger}` removed from"
                    f" {channel.mention}!"
                )
            )
        else:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` does not exists!"
            )

    @config.subcommand(
        "clear",
        sub_cmd_description=(
            "Removes all Truth Bullets from the list of Truth Bullets. This action is"
            " irreversible."
        ),
    )
    async def clear_bullets(self, ctx: utils.THIASlashContext) -> None:
        num_deleted = await models.TruthBullet.prisma().delete_many(
            where={"guild_id": ctx.guild_id}
        )

        # just to give a more clear indication to users
        # technically everything's fine without this
        if num_deleted > 0:
            await ctx.send(
                embed=utils.make_embed("Cleared all Truth Bullets for this server!")
            )
        else:
            raise utils.CustomCheckFailure(
                "There's no Truth Bullets to delete for this server!"
            )

    @config.subcommand(
        "list",
        sub_cmd_description="Lists all Truth Bullets in the server this is run in.",
    )
    async def list_bullets(self, ctx: utils.THIASlashContext) -> None:
        guild_bullets = await models.TruthBullet.prisma().find_many(
            where={"guild_id": ctx.guild_id}
        )
        if not guild_bullets:
            raise utils.CustomCheckFailure("There's no Truth Bullets for this server!")

        bullet_dict: collections.defaultdict[int, list[models.TruthBullet]] = (
            collections.defaultdict(list)
        )
        for bullet in guild_bullets:
            bullet_dict[bullet.channel_id].append(bullet)

        str_builder: collections.deque[str] = collections.deque()

        for channel_id in bullet_dict.keys():
            str_builder.append(f"<#{channel_id}>:")
            for bullet in bullet_dict[channel_id]:
                str_builder.append(
                    f"- `{bullet.trigger}`{' (found)' if bullet.found else ''}"
                )

            str_builder.append("")

        pag = help_tools.HelpPaginator.create_from_list(
            ctx.bot, list(str_builder), timeout=300
        )
        if len(pag.pages) == 1:
            embed = pag.pages[0].to_embed()  # type: ignore
            embed.timestamp = ipy.Timestamp.utcnow()
            embed.color = ctx.bot.color
            embed.title = None
            await ctx.send(embeds=embed)
            return

        pag.show_callback_button = False
        pag.show_select_menu = False
        pag.default_color = ctx.bot.color
        await pag.send(ctx)

    @config.subcommand(
        "info", sub_cmd_description="Lists all information about a Truth Bullet."
    )
    async def bullet_info(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet.", autocomplete=True
        ),
    ) -> None:
        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )
        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` does not exist in"
                f" {channel.mention}!"
            )

        bullet_info = possible_bullet.bullet_info()
        embed = ipy.Embed(
            title="Information about Truth Bullet",
            description=bullet_info,
            color=ctx.bot.color,
            timestamp=ipy.Timestamp.utcnow(),
        )

        await ctx.send(embeds=embed, allowed_mentions=utils.deny_mentions(ctx.author))

    @config.subcommand(
        "edit", sub_cmd_description="Sends a prompt to edit a Truth Bullet."
    )
    @ipy.auto_defer(enabled=False)
    async def edit_bullet(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to edit.", autocomplete=True
        ),
    ) -> None:
        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )
        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` does not exist!"
            )

        modal = ipy.Modal(
            ipy.ShortText(
                label="New trigger",
                custom_id="truth_bullet_trigger",
                value=possible_bullet.trigger,
                max_length=60,
            ),
            ipy.ShortText(
                label="Hide this Truth Bullet only to the finder?",
                custom_id="truth_bullet_hidden",
                value=utils.yesno_friendly_str(possible_bullet.hidden),
                max_length=10,
            ),
            ipy.ParagraphText(
                label="New description",
                custom_id="truth_bullet_desc",
                value=possible_bullet.description,
                max_length=3900,
            ),
            title=(
                f"Edit {name_shorten(possible_bullet.trigger, 10)} for"
                f" #{name_shorten(channel.name, 14)}"
            ),
            custom_id=f"ui:edit-bullet-{channel.id}|{trigger}",
        )
        await ctx.send_modal(modal)
        await ctx.send(
            embed=utils.make_embed(
                f"Sent a popup to edit `{trigger}` for {channel.mention}!"
            )
        )

    @ipy.listen("modal_completion")
    async def on_modal_edit_bullet(self, event: ipy.events.ModalCompletion) -> None:
        ctx = event.ctx

        if ctx.custom_id.startswith("ui:edit-bullet-"):
            channel_id, trigger = ctx.custom_id.removeprefix("ui:edit-bullet-").split(
                "|", maxsplit=1
            )
            channel_id = int(channel_id)

            possible_bullet = await models.TruthBullet.find_possible_bullet(
                channel_id, trigger
            )
            if possible_bullet is None:
                await ctx.send(
                    embed=utils.error_embed_generate(
                        f"Truth Bullet with trigger `{trigger}` no longer exists!"
                    )
                )
                return

            try:
                hidden = convert_to_bool(ctx.responses["truth_bullet_hidden"])
            except ipy.errors.BadArgument:
                await ctx.send(
                    embed=utils.error_embed_generate(
                        "Invalid value for hiding the Truth Bullet! Giving a simple"
                        " 'yes' or 'no' will work."
                    )
                )
                return

            possible_bullet.trigger = ctx.responses["truth_bullet_trigger"]
            possible_bullet.description = ctx.responses["truth_bullet_desc"]
            possible_bullet.hidden = hidden
            await possible_bullet.save()

            if possible_bullet.trigger != trigger:
                await ctx.send(
                    embed=utils.make_embed(
                        f"Edited Truth Bullet `{trigger}` (renamed to"
                        f" `{possible_bullet.trigger}`) in <#{channel_id}>!"
                    )
                )
            else:
                await ctx.send(
                    embed=utils.make_embed(
                        f"Edited Truth Bullet `{trigger}` in <#{channel_id}>!"
                    )
                )

    @config.subcommand("unfind", sub_cmd_description="Un-finds a Truth Bullet.")
    async def unfind_bullet(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to unfind.", autocomplete=True
        ),
    ) -> None:
        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )

        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` does not exist!"
            )
        if not possible_bullet.found:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` has not been found!"
            )

        possible_bullet.found = False
        possible_bullet.finder = None
        await possible_bullet.save()

        await ctx.send(embed=utils.make_embed("Truth Bullet un-found!"))

    @config.subcommand(
        "override",
        sub_cmd_description=(
            "Overrides who found a Truth Bullet with the person specified."
        ),
    )
    async def override_bullet(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to unfind.", autocomplete=True
        ),
        user: ipy.Member = tansy.Option("The user who will find the Truth Bullet."),
    ) -> None:
        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )
        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with `{trigger}` does not exist!"
            )

        possible_bullet.found = True
        possible_bullet.finder = user.id
        await possible_bullet.save()

        await ctx.send(embed=utils.make_embed("Truth Bullet overrided and found!"))

    @config.subcommand(
        "add-alias", sub_cmd_description="Adds an alias to the Truth Bullet specified."
    )
    async def add_alias(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to add an alias to.", autocomplete=True
        ),
        alias: str = tansy.Option(
            "The alias to add. Cannot be over 40 characters.", max_length=40
        ),
    ) -> None:
        if len(alias) > 40:
            raise ipy.errors.BadArgument(
                "The name is too large for me to use! "
                + "Please use something at or under 40 characters."
            )

        if (
            await models.TruthBullet.prisma().count(
                where={
                    "channel_id": channel.id,
                    "trigger": {
                        "equals": models.escape_ilike(alias),
                        "mode": "insensitive",
                    },
                }
            )
            > 0
        ):
            raise ipy.errors.BadArgument(
                f"Alias `{alias}` is used as a trigger for another Truth Bullet for"
                " this channel!"
            )

        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )
        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with trigger `{trigger}` does not exist!"
            )

        if len(possible_bullet.aliases) >= 5:
            raise utils.CustomCheckFailure(
                "Cannot add more aliases to this Truth Bullet!"
            )

        if alias in possible_bullet.aliases:
            raise ipy.errors.BadArgument(
                f"Alias `{alias}` already exists for this Truth Bullet!"
            )

        possible_bullet.aliases.add(alias)
        await possible_bullet.save()

        await ctx.send(
            embed=utils.make_embed(
                f"Alias `{alias}` added to Truth Bullet with trigger `{trigger}` in"
                f" {channel.mention}!"
            )
        )

    @config.subcommand(
        "remove-alias",
        sub_cmd_description="Removes an alias from the Truth Bullet specified.",
    )
    async def remove_alias(
        self,
        ctx: utils.THIASlashContext,
        channel: ipy.GuildText | ipy.GuildPublicThread = tansy.Option(
            "The channel the Truth Bullet is in."
        ),
        trigger: str = tansy.Option(
            "The trigger of the Truth Bullet to remove an alias to.", autocomplete=True
        ),
        alias: str = tansy.Option("The alias to remove.", autocomplete=True),
    ) -> None:
        possible_bullet = await models.TruthBullet.find_possible_bullet(
            channel.id, trigger
        )
        if not possible_bullet:
            raise ipy.errors.BadArgument(
                f"Truth Bullet with `{trigger}` does not exist!"
            )

        try:
            possible_bullet.aliases.remove(alias)
        except KeyError:
            raise ipy.errors.BadArgument(
                f"Alias `{alias}` does not exists for this Truth Bullet!"
            ) from None

        await possible_bullet.save()

        await ctx.send(
            embed=utils.make_embed(
                f"Alias `{alias}` removed from Truth Bullet with trigger `{trigger}` in"
                f" {channel.mention}!"
            )
        )

    @remove_bullet.autocomplete("trigger")
    @bullet_info.autocomplete("trigger")
    @edit_bullet.autocomplete("trigger")
    @unfind_bullet.autocomplete("trigger")
    @override_bullet.autocomplete("trigger")
    @add_alias.autocomplete("trigger")
    @remove_alias.autocomplete("trigger")
    async def _bullet_trigger_autocomplete(self, ctx: ipy.AutocompleteContext) -> None:
        return await fuzzy.autocomplete_bullets(ctx, **ctx.kwargs)

    @remove_alias.autocomplete("alias")
    async def _remove_alias_alias_autocomplete(
        self,
        ctx: ipy.AutocompleteContext,
    ) -> None:
        return await fuzzy.autocomplete_aliases(ctx, **ctx.kwargs)


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    importlib.reload(fuzzy)
    BulletCMDs(bot)
