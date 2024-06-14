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

import common.fuzzy as fuzzy
import common.help_tools as help_tools
import common.models as models
import common.utils as utils


def short_desc(description: str) -> str:
    if len(description) > 25:
        description = f"{description[:22]}..."
    return description


class GachaManagement(utils.Extension):
    def __init__(self, bot: utils.THIABase) -> None:
        self.name = "Gacha Management"
        self.bot: utils.THIABase = bot

    config = tansy.SlashCommand(
        name="gacha-management",
        description="Handles management of gacha mechanics.",
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
        dm_permission=False,
    )

    @config.subcommand(
        "info",
        sub_cmd_description=(
            "Lists out the gacha configuration settings for the server."
        ),
    )
    async def gacha_info(self, ctx: utils.THIASlashContext) -> None:
        config = await ctx.fetch_config({"gacha": True, "names": True})
        if typing.TYPE_CHECKING:
            assert config.gacha is not None
            assert config.names is not None

        str_builder = [
            (
                "Player role:"
                f" {f'<@&{config.player_role}>' if config.player_role else 'N/A'}"
            ),
            f"Gacha status: {utils.toggle_friendly_str(config.gacha.enabled)}",
            f"Gacha use cost:{config.gacha.currency_cost}",
        ]

        embed = utils.make_embed(
            "\n".join(str_builder),
            title=f"Gacha config for {ctx.guild.name}",
        )

        names = (
            f"Singular Currency Name: {config.names.singular_currency_name}\nPlural"
            f" Currency Name: {config.names.plural_currency_name}"
        )

        embed.add_field("Names", names, inline=True)
        await ctx.send(embed=embed)

    @config.subcommand(
        "toggle", sub_cmd_description="Enables or disables the entire gacha system."
    )
    async def gacha_toggle(
        self,
        ctx: utils.THIASlashContext,
        _toggle: str = tansy.Option(
            "Should the gacha system be turned on or off?",
            name="toggle",
            choices=[
                ipy.SlashCommandChoice("on", "on"),
                ipy.SlashCommandChoice("off", "off"),
            ],
        ),
    ) -> None:
        toggle = _toggle == "on"

        if toggle:
            config = await models.GuildConfig.get_or_create(ctx.guild_id)

            if not config.player_role:
                raise utils.CustomCheckFailure(
                    "Player role not set. Please set it with"
                    f" {self.bot.mention_command('config player')} first."
                )

        await models.GachaConfig.prisma().update(
            data={"enabled": toggle}, where={"guild_id": ctx.guild_id}
        )

        await ctx.send(
            embed=utils.make_embed(
                f"Gacha system turned {utils.toggle_friendly_str(toggle)}!"
            )
        )

    @config.subcommand(
        "name",
        sub_cmd_description="Sets the name of the currency to be used.",
    )
    @ipy.auto_defer(enabled=False)
    async def gacha_name(self, ctx: utils.THIASlashContext) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)

        modal = ipy.Modal(
            ipy.InputText(
                label="Singular Currency Name",
                style=ipy.TextStyles.SHORT,
                custom_id="singular_currency_name",
                value=names.singular_currency_name,
                max_length=40,
            ),
            ipy.InputText(
                label="Plural Currency Name",
                style=ipy.TextStyles.SHORT,
                custom_id="plural_currency_name",
                value=names.plural_currency_name,
                max_length=40,
            ),
            title="Edit Currency Names",
            custom_id="currency_names",
        )

        await ctx.send_modal(modal)

    @ipy.modal_callback("currency_names")
    async def currency_names_edit(self, ctx: utils.THIAModalContext) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)

        names.singular_currency_name = ctx.kwargs["singular_currency_name"]
        names.plural_currency_name = ctx.kwargs["plural_currency_name"]
        await names.save()

        await ctx.send(
            embed=utils.make_embed(
                "Updated! Please note this will only affect public-facing"
                f" aspects\nSingular: {names.singular_currency_name}\nPlural:"
                f" {names.plural_currency_name}"
            )
        )

    @config.subcommand(
        "cost", sub_cmd_description="Sets the cost of a single gacha use."
    )
    async def gacha_cost(
        self,
        ctx: utils.THIASlashContext,
        cost: int = tansy.Option("The cost of a single gacha use."),
    ) -> None:
        config = await models.GachaConfig.get_or_create(ctx.guild_id)
        config.currency_cost = cost
        await config.save()

        await ctx.send(
            embed=utils.make_embed(
                f"Updated! The cost of a single gacha use is now {cost}."
            )
        )

    @config.subcommand(
        "give-currency",
        sub_cmd_description="Gives a user a certain amount of currency.",
    )
    async def gacha_give_currency(
        self,
        ctx: utils.THIASlashContext,
        user: ipy.Member = tansy.Option("The user to give currency to."),
        amount: int = tansy.Option("The amount of currency to give."),
    ) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)

        player = await models.GachaPlayer.prisma().upsert(
            where={"user_guild_id": f"{ctx.guild_id}-{user.id}"},
            data={
                "create": {
                    "user_guild_id": f"{ctx.guild_id}-{user.id}",
                    "currency_amount": amount,
                },
                "update": {"currency_amount": {"increment": amount}},
            },
        )

        await ctx.send(
            embed=utils.make_embed(
                f"Gave {amount} {names.currency_name(amount)} to {user.mention}."
                f" New total: {player.currency_amount}."
            )
        )

    @config.subcommand(
        "remov-currency",
        sub_cmd_description="Removes a certain amount of currency from a user.",
    )
    async def gacha_remove_currency(
        self,
        ctx: utils.THIASlashContext,
        user: ipy.Member = tansy.Option(
            "The user to remove currency from.",
        ),
        amount: int = tansy.Option("The amount of currency to remove."),
    ) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)

        player = await models.GachaPlayer.prisma().upsert(
            where={"user_guild_id": f"{ctx.guild_id}-{user.id}"},
            data={
                "create": {
                    "user_guild_id": f"{ctx.guild_id}-{user.id}",
                    "currency_amount": amount,
                },
                "update": {"currency_amount": {"decrement": amount}},
            },
        )

        await ctx.send(
            embed=utils.make_embed(
                f"Removed {amount} {names.currency_name(amount)} from"
                f" {user.mention}. New total: {player.currency_amount}."
            )
        )

    @config.subcommand(
        "reset-currency",
        sub_cmd_description="Resets currency amount for a user.",
    )
    async def gacha_reset_currency(
        self,
        ctx: utils.THIASlashContext,
        user: ipy.Member = tansy.Option(
            "The user to reset currency for.",
            type=ipy.User,
        ),
    ) -> None:
        amount = await models.GachaPlayer.prisma().update_many(
            where={
                "user_guild_id": f"{ctx.guild_id}-{user.id}",
                "currency_amount": {"not": 0},
            },
            data={"currency_amount": 0},
        )

        if amount == 0:
            raise ipy.errors.BadArgument("The user has no currency to reset.")

        await ctx.send(embed=utils.make_embed(f"Reset currency for {user.mention}."))

    @config.subcommand(
        "clear-user",
        sub_cmd_description=(
            "Clears/removes gacha data, including currency and items, for a user."
        ),
    )
    async def gacha_clear_user(
        self,
        ctx: utils.THIASlashContext,
        user: ipy.Member = tansy.Option(
            "The user to clear data for.",
            type=ipy.User,
        ),
    ) -> None:
        amount = await models.GachaPlayer.prisma().delete_many(
            where={
                "user_guild_id": f"{ctx.guild_id}-{user.id}",
            },
        )

        if not amount:
            raise ipy.errors.BadArgument("The user has no data to clear.")

        await ctx.send(
            embed=utils.make_embed(f"Cleared/Removed data for {user.mention}.")
        )

    @config.subcommand(
        "clear-everything",
        sub_cmd_description="Clears ALL gacha user and items data. Use with caution!",
    )
    async def gacha_clear(
        self,
        ctx: utils.THIASlashContext,
        confirm: bool = tansy.Option(
            "Actually clear? Set this to true if you're sure.", default=False
        ),
    ) -> None:
        if not confirm:
            raise ipy.errors.BadArgument(
                "Confirm option not set to true. Please set the option `confirm` to"
                " true to continue."
            )

        players_amount = await models.GachaPlayer.prisma().delete_many(
            where={"user_guild_id": {"startswith": f"{ctx.guild_id}-"}}
        )
        items_amount = await models.GachaItem.prisma().delete_many(
            where={"guild_id": ctx.guild_id}
        )

        if players_amount + items_amount <= 0:
            raise utils.CustomCheckFailure("There's no gacha data to clear!")

        await ctx.send(embed=utils.make_embed("All gacha user and items data cleared."))

    @config.subcommand(
        "give-players",
        sub_cmd_description=(
            "Gives all users with the Player role a certain amount of currency."
        ),
    )
    async def gacha_give_all(
        self,
        ctx: utils.THIASlashContext,
        amount: int = tansy.Option("The amount of currency to give."),
    ) -> None:
        config = await ctx.fetch_config({"names": True})
        if typing.TYPE_CHECKING:
            assert config.names is not None

        if not config.player_role:
            raise utils.CustomCheckFailure(
                "Player role not set. Please set it with"
                f" {self.bot.mention_command('config player')} first."
            )

        actual_role = await ctx.guild.fetch_role(config.player_role)
        if actual_role is None:
            raise utils.CustomCheckFailure("The Player role was not found.")

        if not ctx.guild.chunked:
            await ctx.guild.chunk()

        async with self.bot.db.batch_() as batch:
            for member in actual_role.members:
                batch.prismagachaplayer.upsert(
                    where={"user_guild_id": f"{ctx.guild_id}-{member.id}"},
                    data={
                        "create": {
                            "user_guild_id": f"{ctx.guild_id}-{member.id}",
                            "currency_amount": amount,
                        },
                        "update": {"currency_amount": {"increment": amount}},
                    },
                )

        await ctx.send(
            embed=utils.make_embed(
                f"Gave {amount} {config.names.currency_name(amount)} to all players."
            )
        )

    @config.subcommand(
        "view-all-currencies",
        sub_cmd_description="Views the currency amount of all users.",
    )
    async def gacha_view_all_currencies(self, ctx: utils.THIASlashContext) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)
        players = await models.GachaPlayer.prisma().find_many(
            where={"user_guild_id": {"startswith": f"{ctx.guild_id}-"}}
        )

        if not players:
            raise ipy.errors.BadArgument("No users have data for gacha.")

        str_build: list[str] = []
        str_build.extend(
            f"{player.user_id} -"
            f" {player.currency_amount} {names.currency_name(player.currency_amount)}"
            for player in sorted(players, key=lambda x: x.currency_amount, reverse=True)
        )

        await ctx.send(
            embed=utils.make_embed("\n".join(str_build), title="Gacha Currency Amounts")
        )

    @config.subcommand(
        "view",
        sub_cmd_description="Views the currency amount and items of a user.",
    )
    async def gacha_view(
        self,
        ctx: utils.THIASlashContext,
        user: ipy.Member = tansy.Option(
            "The user to view currency amount and items for.",
            type=ipy.User,
        ),
    ) -> None:
        names = await models.Names.get_or_create(ctx.guild_id)
        player = await models.GachaPlayer.get_or_none(ctx.guild_id, user.id)

        if player is None:
            raise ipy.errors.BadArgument("The user has no data for gacha.")

        items_list = [
            f"**{item.name}** - {short_desc(item.description)}"
            for item in (player.items or [])
        ]
        if len(items_list) > 30:
            chunks = [items_list[x : x + 30] for x in range(0, len(items_list), 30)]
            embeds = [
                utils.make_embed(
                    "\n".join(chunk),
                    title=f"{user.display_name}'s Gacha Data",
                )
                for chunk in chunks
            ]
            embeds[0].description = (
                "Currency:"
                f" {player.currency_amount} {names.currency_name(player.currency_amount)}\n\n**Items:**{embeds[0].description}"
            )

            pag = help_tools.HelpPaginator.create_from_embeds(
                self.bot, *embeds, timeout=120
            )
            await pag.send(ctx)
        else:
            items_list.insert(
                0,
                "Currency:"
                f" {player.currency_amount} {names.currency_name(player.currency_amount)}\n\n**Items:**",
            )

            await ctx.send(
                embed=utils.make_embed(
                    "\n".join(items_list),
                    title="Items",
                )
            )

    @config.subcommand(
        "item-add",
        sub_cmd_description="Adds an item to the gacha.",
    )
    @ipy.auto_defer(enabled=False)
    async def gacha_item_add(
        self,
        ctx: utils.THIASlashContext,
    ) -> None:
        modal = ipy.Modal(
            ipy.InputText(
                label="Item Name",
                style=ipy.TextStyles.SHORT,
                custom_id="item_name",
                max_length=64,
            ),
            ipy.InputText(
                label="Item Description",
                style=ipy.TextStyles.PARAGRAPH,
                custom_id="item_description",
                max_length=1024,
            ),
            ipy.InputText(
                label="Item Amount",
                style=ipy.TextStyles.SHORT,
                custom_id="item_amount",
                max_length=10,
                placeholder="Defaults to being unlimited.",
                required=False,
            ),
            ipy.InputText(
                label="Item Image",
                style=ipy.TextStyles.SHORT,
                custom_id="item_image",
                placeholder="The image URL of the item.",
                required=False,
            ),
            title="Add Gacha Item",
            custom_id="add_gacha_item",
        )
        await ctx.send_modal(modal)

    @ipy.modal_callback("add_gacha_item")
    async def add_gacha_item_modal(self, ctx: utils.THIAModalContext) -> None:
        name: str = ctx.kwargs["item_name"]
        description: str = ctx.kwargs["item_description"]
        str_amount: str = ctx.kwargs.get("item_amount", "-1")
        image: typing.Optional[str] = ctx.kwargs.get("item_image")

        if (
            await models.GachaItem.prisma().count(
                where={"guild_id": ctx.guild_id, "name": name}
            )
            > 0
        ):
            raise ipy.errors.BadArgument("An item with that name already exists.")

        try:
            amount = int(str_amount)
            if amount < -1:
                raise ValueError
        except ValueError:
            raise ipy.errors.BadArgument("Amount must be a positive number.") from None

        await models.GachaItem.prisma().create(
            data={
                "guild_id": ctx.guild_id,
                "name": name,
                "description": description,
                "amount": amount,
                "image": image,
            }
        )

        await ctx.send(embed=utils.make_embed(f"Added item {name} to the gacha."))

    @config.subcommand(
        "item-edit",
        sub_cmd_description="Edits an item in the gacha.",
    )
    @ipy.auto_defer(enabled=False)
    async def gacha_item_edit(
        self,
        ctx: utils.THIASlashContext,
        name: str = tansy.Option("The name of the item to edit.", autocomplete=True),
    ) -> None:
        item = await models.GachaItem.prisma().find_first(
            where={"guild_id": ctx.guild_id, "name": name}
        )
        if item is None:
            raise ipy.errors.BadArgument("No item with that name exists.")

        modal = ipy.Modal(
            ipy.InputText(
                label="Item Name",
                style=ipy.TextStyles.SHORT,
                custom_id="item_name",
                max_length=64,
                value=item.name,
            ),
            ipy.InputText(
                label="Item Description",
                style=ipy.TextStyles.PARAGRAPH,
                custom_id="item_description",
                max_length=1024,
                value=item.description,
            ),
            ipy.InputText(
                label="Item Amount",
                style=ipy.TextStyles.SHORT,
                custom_id="item_amount",
                max_length=10,
                placeholder="Defaults to being unlimited.",
                required=False,
                value=str(item.amount) if item.amount != -1 else ipy.MISSING,
            ),
            ipy.InputText(
                label="Item Image",
                style=ipy.TextStyles.SHORT,
                custom_id="item_image",
                placeholder="The image URL of the item.",
                required=False,
                value=item.image if item.image else ipy.MISSING,
            ),
            title="Edit Gacha Item",
            custom_id=f"edit_gacha_item-{item.id}",
        )
        await ctx.send_modal(modal)

    @ipy.listen("modal_completion")
    async def on_modal_edit_gacha_item(self, event: ipy.events.ModalCompletion) -> None:
        ctx = event.ctx

        if not ctx.custom_id.startswith("edit_gacha_item-"):
            return

        item_id = int(ctx.custom_id.split("-")[1])
        name: str = ctx.kwargs["item_name"]
        description: str = ctx.kwargs["item_description"]
        str_amount: str = ctx.kwargs.get("item_amount", "-1")
        image: typing.Optional[str] = ctx.kwargs.get("item_image")

        if not await models.GachaItem.prisma().count(where={"id": item_id}):
            raise ipy.errors.BadArgument("The item no longer exists.")

        try:
            amount = int(str_amount)
            if amount < -1:
                raise ValueError
        except ValueError:
            raise ipy.errors.BadArgument("Amount must be a positive number.") from None

        await models.GachaItem.prisma().update(
            data={
                "name": name,
                "description": description,
                "amount": amount,
                "image": image,
            },
            where={"id": item_id},
        )

        await ctx.send(embed=utils.make_embed(f"Edit item {name}."))

    @config.subcommand(
        "item-remove",
        sub_cmd_description="Removes an item from the gacha.",
    )
    async def gacha_item_remove(
        self,
        ctx: utils.THIASlashContext,
        name: str = tansy.Option("The name of the item to remove.", autocomplete=True),
    ) -> None:
        amount = await models.GachaItem.prisma().delete_many(
            where={"guild_id": ctx.guild_id, "name": name}
        )
        if amount <= 0:
            raise ipy.errors.BadArgument("No item with that name exists.")

        await ctx.send(f"Deleted {name}.")

    @config.subcommand(
        "view-items", sub_cmd_description="Views all gacha items for this server."
    )
    async def gacha_view_items(
        self,
        ctx: utils.THIASlashContext,
    ) -> None:
        items = await models.GachaItem.prisma().find_many(
            where={"guild_id": ctx.guild_id}
        )

        if not items:
            raise utils.CustomCheckFailure("This server has no items to show.")

        items_list = [
            f"**{i.name}**{f' ({i.amount} remaining)' if i.amount else ''}:"
            f" {short_desc(i.description)}"
            for i in items
        ]
        if len(items_list) > 30:
            chunks = [items_list[x : x + 30] for x in range(0, len(items_list), 30)]
            embeds = [
                utils.make_embed(
                    "\n".join(chunk),
                    title="Items",
                )
                for chunk in chunks
            ]

            pag = help_tools.HelpPaginator.create_from_embeds(
                self.bot, *embeds, timeout=120
            )
            await pag.send(ctx)
        else:
            await ctx.send(
                embed=utils.make_embed(
                    "\n".join(items_list),
                    title="Items",
                )
            )

    @gacha_item_edit.autocomplete("name")
    @gacha_item_remove.autocomplete("name")
    async def _autocomplete_gacha_items(
        self,
        ctx: ipy.AutocompleteContext,
    ) -> None:
        return await fuzzy.autocomplete_bullets(ctx, **ctx.kwargs)


def setup(bot: utils.THIABase) -> None:
    importlib.reload(utils)
    importlib.reload(fuzzy)
    importlib.reload(help_tools)
    GachaManagement(bot)
