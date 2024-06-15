"""
Copyright 2021-2024 AstreaTSS.
This file is part of PYTHIA, formerly known as Ultimate Investigator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import os
import re
import typing
from enum import IntEnum

import interactions as ipy
import orjson
from prisma._async_http import Response
from prisma.models import (
    PrismaBulletConfig,
    PrismaGachaConfig,
    PrismaGachaItem,
    PrismaGachaPlayer,
    PrismaGuildConfig,
    PrismaNames,
    PrismaTruthBullet,
)
from prisma.types import (
    PrismaGachaPlayerInclude,
    PrismaGuildConfigInclude,
    PrismaGuildConfigUpdateInput,
)
from pydantic import field_serializer, field_validator


# yes, this is a copy from common.utils
# but circular imports are a thing
def yesno_friendly_str(bool_to_convert: bool) -> str:
    return "yes" if bool_to_convert else "no"


def generate_regexp(attribute: str) -> str:
    return rf"regexp_replace({attribute}, '([\%_])', '\\\1', 'g')"


ILIKE_ESCAPE = re.compile(r"([\%_])")


def escape_ilike(value: str) -> str:
    return ILIKE_ESCAPE.sub(r"\\\1", value)


TEMPLATE_MARKDOWN = re.compile(r"({{(.*)}})")


def code_template(value: str) -> str:
    return TEMPLATE_MARKDOWN.sub(r"`\1`", value)


def short_desc(description: str, length: int = 25) -> str:
    if len(description) > length:
        description = f"{description[:length-3]}..."
    return description


class TruthBullet(PrismaTruthBullet):
    aliases: set[str]

    @field_validator("aliases", mode="after")
    @classmethod
    def _transform_aliases_into_set(cls, value: list[str]) -> set[str]:
        return set(value)

    @field_serializer("aliases", when_used="always")
    def _transform_aliases_into_list(self, value: set[str]) -> list[str]:
        return sorted(value)

    @property
    def chan_mention(self) -> str:
        return f"<#{self.channel_id}>"

    def bullet_info(self) -> str:
        str_list = [
            f"Trigger `{self.trigger}` - in {self.chan_mention}",
            f"Aliases: {', '.join(f'`{a}`' for a in self.aliases)}",
            f"Hidden: {yesno_friendly_str(self.hidden)}",
            f"Found: {yesno_friendly_str(self.found)}",
        ]

        str_list.extend(
            (
                f"Finder: {f'<@{self.finder}>' if self.finder else 'N/A'}",
                "",
                f"Description: {self.description}",
            )
        )

        return "\n".join(str_list)

    def found_embed(self, username: str, singular_bullet: str) -> ipy.Embed:
        embed = ipy.Embed(
            title=f"{singular_bullet} Discovered",
            timestamp=ipy.Timestamp.utcnow(),
            color=int(os.environ["BOT_COLOR"]),
        )
        embed.description = (
            f"`{self.trigger}` - from {self.chan_mention}\n\n{self.description}"
        )

        footer = f"Found by {username}" if self.finder else "To be found as of"
        embed.set_footer(text=footer)

        return embed

    @classmethod
    async def find(
        cls, channel_id: ipy.Snowflake_Type, content: str
    ) -> typing.Self | None:
        return await cls.prisma().query_first(
            FIND_TRUTH_BULLET_STR, int(channel_id), content
        )

    @classmethod
    async def find_exact(
        cls, channel_id: ipy.Snowflake_Type, content: str
    ) -> typing.Self | None:
        return await cls.prisma().query_first(
            FIND_TRUTH_BULLET_EXACT_STR, int(channel_id), content
        )

    @classmethod
    async def find_possible_bullet(
        cls, channel_id: ipy.Snowflake_Type, trigger: str
    ) -> typing.Self | None:
        return await cls.prisma().find_first(
            where={
                "channel_id": int(channel_id),
                "trigger": {"equals": escape_ilike(trigger), "mode": "insensitive"},
            }
        )

    @classmethod
    async def validate(cls, channel_id: ipy.Snowflake_Type, trigger: str) -> bool:
        return (
            await cls.prisma()._client.query_first(
                VALIDATE_TRUTH_BULLET_STR, int(channel_id), trigger
            )
            is not None
        )

    async def save(self) -> None:
        data = self.model_dump()
        await self.prisma().update(where={"id": self.id}, data=data)  # type: ignore


class GetMethodsMixin:
    @classmethod
    async def get(cls, guild_id: int) -> typing.Self:
        return await cls.prisma().find_unique_or_raise(where={"guild_id": guild_id})

    @classmethod
    async def get_or_none(cls, guild_id: int) -> typing.Optional[typing.Self]:
        return await cls.prisma().find_unique(where={"guild_id": guild_id})

    @classmethod
    async def get_or_create(cls, guild_id: int) -> typing.Self:
        return await cls.get_or_none(guild_id) or await cls.prisma().create(
            data={"guild_id": guild_id}
        )


class Names(GetMethodsMixin, PrismaNames):
    main_config: "typing.Optional[GuildConfig]" = None

    def currency_name(self, amount: int) -> str:
        return self.singular_currency_name if amount == 1 else self.plural_currency_name

    async def save(self) -> None:
        data = self.model_dump(exclude={"main_config"})
        await self.prisma().update(where={"guild_id": self.guild_id}, data=data)  # type: ignore


class InvestigationType(IntEnum):
    DEFAULT = 1
    COMMAND_ONLY = 2


class BulletConfig(GetMethodsMixin, PrismaBulletConfig):
    investigation_type: InvestigationType
    main_config: "typing.Optional[GuildConfig]" = None

    @field_validator("investigation_type", mode="after")
    @classmethod
    def _transform_int_into_investigation_type(cls, value: int) -> InvestigationType:
        return InvestigationType(value)

    @field_serializer("investigation_type", when_used="always")
    def _transform_investigation_type_into_int(self, value: InvestigationType) -> int:
        return value.value

    async def save(self) -> None:
        data = self.model_dump(exclude={"main_config"})
        await self.prisma().update(where={"guild_id": self.guild_id}, data=data)  # type: ignore


class GachaItem(PrismaGachaItem):
    players: "typing.Optional[list[GachaPlayer]]" = None
    gacha_config: "typing.Optional[GachaConfig]" = None

    def embed(self, *, show_amount: bool = False) -> ipy.Embed:
        embed = ipy.Embed(
            title=self.name,
            description=self.description,
            color=ipy.Color(int(os.environ["BOT_COLOR"])),
            timestamp=ipy.Timestamp.utcnow(),
        )
        if self.image:
            embed.set_thumbnail(self.image)

        if show_amount:
            embed.add_field(
                name="Amount Remaining",
                value=self.amount if self.amount != -1 else "Unlimited",
                inline=True,
            )

        return embed

    async def save(self) -> None:
        data = self.model_dump(exclude={"gacha_config", "players"})
        await self.prisma().update(where={"id": self.id}, data=data)  # type: ignore


class GachaPlayer(PrismaGachaPlayer):
    items: "typing.Optional[list[GachaItem]]" = None

    @classmethod
    async def get(
        cls,
        guild_id: int,
        user_id: int,
        include: PrismaGachaPlayerInclude | None = None,
    ) -> typing.Self:
        return await cls.prisma().find_unique_or_raise(
            where={"guild_user_id": f"{guild_id}-{user_id}"}, include=include
        )

    @classmethod
    async def get_or_none(
        cls,
        guild_id: int,
        user_id: int,
        include: PrismaGachaPlayerInclude | None = None,
    ) -> typing.Optional[typing.Self]:
        return await cls.prisma().find_unique(
            where={"guild_user_id": f"{guild_id}-{user_id}"}, include=include
        )

    @classmethod
    async def get_or_create(
        cls,
        guild_id: int,
        user_id: int,
        include: PrismaGachaPlayerInclude | None = None,
    ) -> typing.Self:
        return await cls.get_or_none(
            guild_id, user_id, include=include
        ) or await cls.prisma().create(data={"guild_user_id": f"{guild_id}-{user_id}"})

    @property
    def guild_id(self) -> int:
        return int(self.guild_user_id.split("-")[0])

    @property
    def user_id(self) -> int:
        return int(self.guild_user_id.split("-")[1])

    def create_profile(self, user_display_name: str, names: "Names") -> list[ipy.Embed]:
        str_builder = [
            (
                "Currency:"
                f" {self.currency_amount} {names.currency_name(self.currency_amount)}"
            ),
            "\n**Items:**",
        ]

        if self.items:
            str_builder.extend(
                f"**{item.name}** - {short_desc(item.description)}"
                for item in self.items
            )
        else:
            str_builder.append("*No items.*")

        if len(str_builder) <= 30:
            return [
                ipy.Embed(
                    title=f"{user_display_name}'s Gacha Data",
                    description="\n".join(str_builder),
                    color=ipy.Color(int(os.environ["BOT_COLOR"])),
                    timestamp=ipy.Timestamp.utcnow(),
                )
            ]

        chunks = [str_builder[x : x + 30] for x in range(0, len(str_builder), 30)]
        return [
            ipy.Embed(
                title=f"{user_display_name}'s Gacha Data",
                description="\n".join(chunk),
                color=ipy.Color(int(os.environ["BOT_COLOR"])),
                timestamp=ipy.Timestamp.utcnow(),
            )
            for chunk in chunks
        ]

    async def save(self) -> None:
        data = self.model_dump(
            exclude={
                "items",
            }
        )
        await self.prisma().update(where={"guild_user_id": self.guild_user_id}, data=data)  # type: ignore


class GachaConfig(GetMethodsMixin, PrismaGachaConfig):
    items: "typing.Optional[list[GachaItem]]" = None
    main_config: "typing.Optional[GuildConfig]" = None

    async def save(self) -> None:
        data = self.model_dump(exclude={"main_config"})
        await self.prisma().update(where={"guild_id": self.guild_id}, data=data)  # type: ignore


class GuildConfigMixin:
    guild_id: ipy.Snowflake

    if typing.TYPE_CHECKING:
        from prisma import actions

        @classmethod
        def prisma(cls) -> actions.PrismaGuildConfigActions[typing.Self]: ...

        model_dump: typing.Callable[..., dict[str, typing.Any]]

    async def _fill_in_include(
        self, include: PrismaGuildConfigInclude | None
    ) -> typing.Self:
        config = self

        if not include:
            return self

        add_data: PrismaGuildConfigUpdateInput = {}

        for entry in include:
            if entry == "names" and not getattr(self, "names", True):
                add_data["names"] = {"create": {"guild_id": self.guild_id}}
            if entry == "bullets" and not getattr(self, "bullets", True):
                add_data["bullets"] = {"create": {"guild_id": self.guild_id}}
            if entry == "gacha" and not getattr(self, "gacha", True):
                add_data["gacha"] = {"create": {"guild_id": self.guild_id}}

        if add_data:
            config = await self.prisma().update(
                where={"guild_id": self.guild_id},
                data=add_data,
                include=include,
            )
            if typing.TYPE_CHECKING:
                assert config is not None

        return self

    @classmethod
    async def get(
        cls, guild_id: int, include: PrismaGuildConfigInclude | None = None
    ) -> typing.Self:
        config = await cls.prisma().find_unique_or_raise(
            where={"guild_id": guild_id},
            include=include,
        )
        return await config._fill_in_include(include)

    @classmethod
    async def get_or_none(
        cls, guild_id: int, include: PrismaGuildConfigInclude | None = None
    ) -> typing.Optional[typing.Self]:
        config = await cls.prisma().find_unique(
            where={"guild_id": guild_id}, include=include
        )

        if config:
            config = await config._fill_in_include(include)

        return config

    @classmethod
    async def get_or_create(
        cls, guild_id: int, include: PrismaGuildConfigInclude | None = None
    ) -> typing.Self:
        config = await cls.prisma().find_unique(
            where={"guild_id": guild_id}, include=include
        ) or await cls.prisma().create(data={"guild_id": guild_id})
        return await config._fill_in_include(include)

    async def save(self) -> None:
        data = self.model_dump(exclude={"names", "names_id", "bullets", "guild_id"})
        await self.prisma().update(where={"guild_id": self.guild_id}, data=data)  # type: ignore


class GuildConfig(GuildConfigMixin, PrismaGuildConfig):
    bullets: typing.Optional[BulletConfig] = None
    names: typing.Optional[Names] = None


FIND_TRUTH_BULLET_STR: typing.Final[str] = (
    f"""
SELECT
    {', '.join(TruthBullet.model_fields)}
FROM
    thiabulletconfig
WHERE
    channel_id = $1
    AND found = false
    AND (
        $2 ILIKE CONCAT('%', {generate_regexp('trigger')}, '%')
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE $2 ILIKE CONCAT('%', {generate_regexp('alias')}, '%')
        )
    );
""".strip()  # noqa: S608
)

VALIDATE_TRUTH_BULLET_STR: typing.Final[str] = (
    """
SELECT
    1
FROM
    thiabulletconfig
WHERE
    channel_id = $1
    AND (
        UPPER($2) = UPPER(trigger)
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE UPPER($2) = UPPER(alias)
        )
    );
""".strip()
)

FIND_TRUTH_BULLET_EXACT_STR: typing.Final[str] = (
    f"""
SELECT
    {', '.join(TruthBullet.model_fields)}
FROM
    thiabulletconfig
WHERE
    channel_id = $1
    AND (
        UPPER($2) = UPPER(trigger)
        OR EXISTS (
            SELECT 1
            FROM unnest(aliases) AS alias
            WHERE UPPER($2) = UPPER(alias)
        )
    );
""".strip()  # noqa: S608
)


class FastResponse(Response):
    async def json(self, **kwargs: typing.Any) -> typing.Any:
        return orjson.loads(await self.original.aread(), **kwargs)


Response.json = FastResponse.json  # type: ignore


Names.model_rebuild()
BulletConfig.model_rebuild()
GachaItem.model_rebuild()
GachaConfig.model_rebuild()
GachaPlayer.model_rebuild()
