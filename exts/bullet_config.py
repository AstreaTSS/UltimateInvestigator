"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import importlib
import typing

import interactions as ipy
import tansy
from interactions.client.mixins.send import SendMixin

import common.models as models
import common.utils as utils


class BulletConfigCMDs(utils.Extension):
    """Commands for using and modifying Truth Bullet server settings."""

    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "Bullet Config"
        self.bot: utils.THIABase = bot

    config = tansy.SlashCommand(
        name="config",
        description="Handles configuration of the bot.",  # type: ignore
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
        dm_permission=False,
    )

    @config.subcommand(
        sub_cmd_name="info",
        sub_cmd_description=(
            "Lists out the Truth Bullet configuration settings for the server."
        ),
    )
    async def bullet_config(self, ctx: utils.THIASlashContext) -> None:
        config = await ctx.fetch_config({"bullets": True, "names": True})
        if typing.TYPE_CHECKING:
            assert config.bullets is not None
            assert config.names is not None

        str_builder = [
            (
                "Player role:"
                f" {f'<@&{config.player_role}>' if config.player_role else 'N/A'}"
            ),
            (
                "Truth Bullets:"
                f" {utils.toggle_friendly_str(config.bullets.bullets_enabled)}"
            ),
            (
                "Truth Bullet channel:"
                f" {f'<#{config.bullets.bullet_chan_id}>' if config.bullets.bullet_chan_id else 'N/A'}"
            ),
            (
                "Investigation mode:"
                f" {config.bullets.investigation_type.name.replace('_', ' ').title()}"
            ),
            (
                "Best Truth Bullet Finder role:"
                f" {f'<@&{config.bullets.best_bullet_finder_role}>' if config.bullets.best_bullet_finder_role else 'N/A'}"
            ),
        ]

        embed = ipy.Embed(
            title=f"Investigation config for {ctx.guild.name}",
            description="\n".join(str_builder),
            color=utils._bot_color,
            timestamp=ipy.Timestamp.utcnow(),
        )

        names_builder: list[str] = [
            (
                f"Singular Truth Bullet: {config.names.singular_bullet}\nPlural Truth"
                f" Bullet: {config.names.plural_bullet}\nSingular Truth Bullet Finder:"
                f" {models.code_template(config.names.singular_truth_bullet_finder)}\nPlural"
                " Truth Bullet Finder:"
                f" {models.code_template(config.names.plural_truth_bullet_finder)}\nBest"
                " Truth Bullet Finder:"
                f" {models.code_template(config.names.best_bullet_finder)}"
            ),
            (
                "*Note: anything in `{{}}` is a field to be replaced dynamically by the"
                " appropriate value.*"
            ),
        ]
        embed.add_field("Names", "\n".join(names_builder), inline=True)
        await ctx.send(embed=embed)

    @config.subcommand(
        sub_cmd_name="bullet-channel",
        sub_cmd_description="Sets (or unsets) where all Truth Bullets are sent to.",
    )
    async def set_bullet_channel(
        self,
        ctx: utils.THIASlashContext,
        channel: typing.Optional[ipy.GuildText] = tansy.Option(
            "The channel to send Truth Bullets to.", default=None
        ),
        unset: bool = tansy.Option(
            "Should the Truth Bullet channel be unset?", default=False
        ),
    ) -> None:
        if not (bool(channel) ^ unset):
            raise ipy.errors.BadArgument(
                "You must set a Truth Bullet channel or specify to unset it."
            )

        if channel and not isinstance(channel, SendMixin):
            raise ipy.errors.BadArgument("The channel must be a text channel.")

        bullet_config = await models.BulletConfig.get_or_create(ctx.guild_id)
        bullet_config.bullet_chan_id = channel.id if channel else None
        await bullet_config.save()

        if channel:
            await ctx.send(
                embed=utils.make_embed(
                    f"Truth Bullet channel set to {channel.mention}!"
                )
            )
        else:
            await ctx.send(embed=utils.make_embed("Truth Bullet channel unset."))

    @config.subcommand(
        sub_cmd_name="best-truth-bullet-finder",
        sub_cmd_description="Sets (or unsets) the Best Truth Bullet Finder role.",
    )
    async def set_best_truth_bullet_finder_role(
        self,
        ctx: utils.THIASlashContext,
        role: typing.Optional[ipy.Role] = tansy.Option(
            "The Best Detective role to use.",
            converter=utils.ValidRoleConverter,
            default=None,
        ),
        unset: bool = tansy.Option("Should the role be unset?", default=False),
    ) -> None:
        if not (bool(role) ^ unset):
            raise ipy.errors.BadArgument(
                "You must either specify a role or specify to unset the role."
            )

        bullet_config = await models.BulletConfig.get_or_create(ctx.guild_id)
        bullet_config.best_bullet_finder_role = role.id if role else None
        await bullet_config.save()

        if role:
            await ctx.send(
                embed=utils.make_embed(
                    f"Best Truth Bullet Finder role set to {role.mention}!"
                ),
            )
        else:
            await ctx.send(
                embed=utils.make_embed("Best Truth Bullet Finder role unset.")
            )

    @config.subcommand(
        sub_cmd_name="player",
        sub_cmd_description=(
            "Sets (or unsets) the Player role, the role that can find Truth Bullets."
        ),
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
        sub_cmd_name="investigation-mode",
        sub_cmd_description="Change the investigation mode.",
    )
    async def set_investigation_mode(
        self,
        ctx: utils.THIASlashContext,
        mode: int = tansy.Option(
            "The investigation mode to set.",
            choices=[
                ipy.SlashCommandChoice("Default", models.InvestigationType.DEFAULT),
                ipy.SlashCommandChoice(
                    "/investigate command only", models.InvestigationType.COMMAND_ONLY
                ),
            ],
        ),
    ) -> None:
        try:
            investigation_type = models.InvestigationType(mode)
        except ValueError:
            raise ipy.errors.BadArgument("Invalid investigation mode.") from None

        bullet_config = await models.BulletConfig.get_or_create(ctx.guild_id)
        bullet_config.investigation_type = investigation_type
        await bullet_config.save()

        if investigation_type == models.InvestigationType.COMMAND_ONLY:
            self.bot.msg_enabled_bullets_guilds.discard(int(ctx.guild.id))
        elif bullet_config.bullets_enabled:
            self.bot.msg_enabled_bullets_guilds.add(int(ctx.guild.id))

        await ctx.send(
            embed=utils.make_embed(
                "Investigation mode set to"
                f" {bullet_config.investigation_type.name.replace('_', ' ').title()}."
            )
        )

    @config.subcommand(
        sub_cmd_name="names",
        sub_cmd_description="Edit the names used for various parts of the bot.",
    )
    @ipy.auto_defer(enabled=False)
    async def edit_names(
        self,
        ctx: utils.THIASlashContext,
        to_change: str = tansy.Option(
            "The names to change.",
            choices=[
                ipy.SlashCommandChoice("Truth Bullet Names", "bullet_names"),
                ipy.SlashCommandChoice("Truth Bullet Finders", "bullet_finders"),
            ],
        ),
    ) -> None:
        if to_change not in {"bullet_names", "bullet_finders"}:
            raise ipy.errors.BadArgument("Invalid change requested!")

        config = await ctx.fetch_config({"names": True})
        if typing.TYPE_CHECKING:
            assert config.names is not None

        if to_change == "bullet_names":
            modal = ipy.Modal(
                ipy.InputText(
                    label="Singular Bullet Name",
                    style=ipy.TextStyles.SHORT,
                    custom_id="singular_name",
                    value=config.names.singular_bullet,
                    max_length=40,
                ),
                ipy.InputText(
                    label="Plural Bullet Name",
                    style=ipy.TextStyles.SHORT,
                    custom_id="plural_name",
                    value=config.names.plural_bullet,
                    max_length=40,
                ),
                title="Edit Truth Bullet Names",
                custom_id="bullet_names",
            )
        else:
            modal = ipy.Modal(
                ipy.InputText(
                    label="Singular Truth Bullet Finder",
                    style=ipy.TextStyles.SHORT,
                    custom_id="singular_truth_bullet_finder",
                    value=config.names.singular_truth_bullet_finder,
                    max_length=70,
                ),
                ipy.InputText(
                    label="Plural Truth Bullet Finder",
                    style=ipy.TextStyles.SHORT,
                    custom_id="plural_truth_bullet_finder",
                    value=config.names.plural_truth_bullet_finder,
                    max_length=70,
                ),
                ipy.InputText(
                    label="Best Bullet Finder Name",
                    style=ipy.TextStyles.SHORT,
                    custom_id="best_bullet_finder",
                    value=config.names.best_bullet_finder,
                    max_length=70,
                ),
                title="Edit Truth Bullet Finder Names",
                custom_id="bullet_finders",
            )

        await ctx.send_modal(modal)

    @ipy.modal_callback("bullet_names")
    async def bullet_names_edit(self, ctx: utils.THIAModalContext) -> None:
        config = await ctx.fetch_config({"names": True})
        if typing.TYPE_CHECKING:
            assert config.names is not None
        names = config.names

        names.singular_bullet = ctx.kwargs["singular_name"]
        names.plural_bullet = ctx.kwargs["plural_name"]
        await config.names.save()

        await ctx.send(
            embed=utils.make_embed(
                "Updated! Please note this will only affect public-facing aspects - IE"
                f" finding items.\nSingular: {names.singular_bullet}\nPlural:"
                f" {names.plural_bullet}"
            )
        )

    @ipy.modal_callback("bullet_finders")
    async def bullet_finders_edit(self, ctx: utils.THIAModalContext) -> None:
        config = await ctx.fetch_config({"names": True})
        if typing.TYPE_CHECKING:
            assert config.names is not None
        names = config.names

        if (
            var_name := models.TEMPLATE_MARKDOWN.search(
                ctx.kwargs["singular_truth_bullet_finder"]
            )
        ) and var_name.group(2) != "bullet_name":
            raise ipy.errors.BadArgument(
                "Invalid variable name in Singular Truth Bullet Finder. Only"
                " `{{bullet_name}}`, the Truth Bullet name, is allowed."
            )

        if (
            var_name := models.TEMPLATE_MARKDOWN.search(
                ctx.kwargs["plural_truth_bullet_finder"]
            )
        ) and var_name.group(2) != "bullet_name":
            raise ipy.errors.BadArgument(
                "Invalid variable name in Plural Truth Bullet Finder. Only"
                " `{{bullet_name}}`, the Truth Bullet name, is allowed."
            )

        if (
            var_name := models.TEMPLATE_MARKDOWN.search(
                ctx.kwargs["best_bullet_finder"]
            )
        ) and var_name.group(2) != "bullet_finder":
            raise ipy.errors.BadArgument(
                "Invalid variable name in Best Truth Bullet Finder. Only"
                " `{{bullet_finder}}`, the Truth Bullet Finder name, is allowed."
            )

        names.singular_truth_bullet_finder = ctx.kwargs["singular_truth_bullet_finder"]
        names.plural_truth_bullet_finder = ctx.kwargs["plural_truth_bullet_finder"]
        names.best_bullet_finder = ctx.kwargs["best_bullet_finder"]
        await names.save()

        await ctx.send(
            embed=utils.make_embed(
                "Updated! Please note this will only affect public-facing aspects - IE"
                " finding all items.\nSingular Finder:"
                f" {models.code_template(names.singular_truth_bullet_finder)}\nPlural"
                " Finders:"
                f" {models.code_template(names.plural_truth_bullet_finder)}\nBest"
                f" Finder: {models.code_template(names.best_bullet_finder)}\n\n*Note:"
                " anything in `{}` is a field to be replaced dynamically by the"
                " appropriate value.*",
            )
        )

    def enable_check(self, config: models.GuildConfig) -> None:
        if not config.player_role:
            raise utils.CustomCheckFailure(
                "You still need to set the Player role for this server!"
            )
        elif not config.bullets or not config.bullets.bullet_chan_id:
            raise utils.CustomCheckFailure(
                "You still need to set a Truth Bullets channel!"
            )

    @config.subcommand(
        sub_cmd_name="toggle",
        sub_cmd_description="Turns on or off the Truth Bullets.",
    )
    async def toggle_bullets(
        self,
        ctx: utils.THIASlashContext,
        toggle: bool = tansy.Option(
            "Should the Truth Bullets be on (true) or off (false)?"
        ),
    ) -> None:
        config = await ctx.fetch_config({"bullets": True})
        if typing.TYPE_CHECKING:
            assert config.bullets is not None

        if (
            not config.bullets.bullets_enabled and toggle
        ):  # if truth bullets will be enabled by this
            self.enable_check(config)

        config.bullets.bullets_enabled = toggle
        await config.bullets.save()

        if config.bullets.investigation_type != models.InvestigationType.COMMAND_ONLY:
            if toggle:
                self.bot.msg_enabled_bullets_guilds.add(int(ctx.guild.id))
            else:
                self.bot.msg_enabled_bullets_guilds.discard(int(ctx.guild.id))

        await ctx.send(
            embed=utils.make_embed(
                "Truth Bullets turned"
                f" {utils.toggle_friendly_str(config.bullets.bullets_enabled)}!"
            )
        )

    @config.subcommand(
        sub_cmd_name="help",
        sub_cmd_description="Tells you how to set up this bot.",
    )
    async def setup_help(
        self,
        ctx: utils.THIASlashContext,
    ) -> None:
        embed = utils.make_embed(
            "To set up this bot, follow the Server Setup Guide below.",
            title="Setup Bot",
        )
        button = ipy.Button(
            style=ipy.ButtonStyle.LINK,
            label="Server Setup Guide",
            url="https://pythia.astrea.cc/server_setup.html",
        )
        await ctx.send(embeds=embed, components=button)


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    BulletConfigCMDs(bot)
