from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Literal

import discord
from discord.http import Route
from redbot.core import Config, commands


log = logging.getLogger("red.nebula.NebulaReminderCore")

IS_COMPONENTS_V2 = 1 << 15
EPHEMERAL = 1 << 6

ARROW_LEFT_ID = "1498458221105643602"
ARROW_LEFT_LEFT_ID = "1516972809694220449"
REFRESH_ID = "1498458217477570560"
ARROW_RIGHT_ID = "1498458218668621854"
ARROW_RIGHT_RIGHT_ID = "1516972536665997422"

PAGE_COUNT = 5

REMINDER_SETTINGS: list[tuple[str, str, str, str]] = [
    (
        "work_shift",
        "Work Shift Reminder",
        "WorkShiftReminder",
        "Get a reminder when work shift is ready.",
    ),
    (
        "scratch",
        "Scratch Reminder",
        "ScratchReminder",
        "Get a reminder when scratch is available again.",
    ),
    (
        "pets_activity",
        "Pets Activity Reminder",
        "PetActivityReminder",
        "Get a reminder when pets activity is ready again.",
    ),
    (
        "items",
        "Item Reminders",
        "ItemReminderGroup",
        "Get reminders when tracked usable items are ready again.",
    ),
    (
        "adventure",
        "Adventure Reminder",
        "AdventureReminder",
        "Get a reminder when your next adventure is ready.",
    ),
    (
        "farm",
        "Farm Reminder",
        "FarmRemind",
        "Get a reminder when your crops are ready to harvest.",
    ),
    (
        "giveaway",
        "Giveaway Reminder",
        "GiveawayReminder",
        "Get a reminder when giveaway create is ready again.",
    ),
    (
        "collector_rewards",
        "Collector Rewards Reminder",
        "CollectorRewardReminder",
        "Get a reminder when collector rewards can be claimed again.",
    ),
    (
        "marriage",
        "Marriage Upkeep Reminder",
        "MarriageReminder",
        "Get a reminder when marriage upkeep needs attention.",
    ),
    (
        "stream",
        "Stream Reminder",
        "StreamReminder",
        "Get stream interaction reminders and ending warnings.",
    ),
    (
        "fish_boosts",
        "Fish Boosts Reminder",
        "FishBoostsReminder",
        "Get a reminder when fish boosts rotate.",
    ),
    (
        "summon_npc",
        "Summon NPC Reminder",
        "NpcSummonReminder",
        "Get a reminder to summon NPC",
    ),
]

ASSISTANT_SETTINGS: list[tuple[str, str, str, str]] = [
    (
        "work_shift",
        "Work Shift Assistant",
        "WorkShiftReminder",
        "Show helper prompts for work shift mini games.",
    ),
    (
        "pet_minigame",
        "Pets Care Assistant",
        "PetMinigameAssistant",
        "Show helper prompts for pets care mini games.",
    ),
    (
        "adventure",
        "Adventure Assistant",
        "AdventureAssistant",
        "Show a helper guide for adventures.",
    ),
    (
        "npc_interaction",
        "NPC Interaction Assistant",
        "NPCInteractionAssistant",
        "Show helper prompts for NPC interactions.",
    ),
    (
        "trivia",
        "Trivia Assistant",
        "TriviaAssistant",
        "Show helper prompts for trivia questions.",
    ),
    (
        "market_assistant",
        "Market Assistant",
        "MarketAssistant",
        "Show value and gain helpers for Dank Memer market view listings.",
    ),
    (
        "lootbox_assistant",
        "Loot Box Assistant",
        "LootBoxAssistant",
        "Show net profit helpers for Dank Memer loot box openings.",
    ),
]

CLAIM_SETTINGS: list[tuple[str, str, str]] = [
    (
        "daily",
        "Daily Claim",
        "Get a reminder to claim daily coins.",
    ),
    (
        "weekly",
        "Weekly Claim",
        "Get a reminder to claim weekly coins.",
    ),
    (
        "monthly",
        "Monthly Claim",
        "Get a reminder to claim monthly coins.",
    ),
]

CMD_REMINDER_SETTINGS: list[tuple[str, str, str, str, float, float]] = [
    (
        "tidy",
        "Tidy",
        "</tidy:1388145631587209358>",
        "Reminder when tidy is ready again.",
        12.0,
        25.0,
    ),
    (
        "dig",
        "Dig",
        "</dig:1011560371078832204>",
        "Reminder when dig is ready again.",
        10.0,
        20.0,
    ),
    (
        "hunt",
        "Hunt",
        "</hunt:1011560371171102760>",
        "Reminder when hunt is ready again.",
        10.0,
        20.0,
    ),
]

ITEM_REMINDER_SETTINGS: list[tuple[str, str, str, str, bool]] = [
    (
        "instantcrafting",
        "<:InstantCrafting:1521754813698670703> Instant Crafting",
        "InstantCraftingReminder",
        "Get a reminder to buy Instant Crafting.",
        True,
    ),
    (
        "instantfarming",
        "<:InstantFarming:1521754812142587965> Instant Farming",
        "InstantFarmingReminder",
        "Get a reminder to buy Instant Farming.",
        True,
    ),
    (
        "omegabait",
        "<a:OmegaBaitFBE:1521754802340495451> Omega Bait",
        "OmegaBaitReminder",
        "Get a reminder to buy Omega Bait.",
        True,
    ),
    (
        "stonkmachine",
        "<a:StonksMachine:1507484236104466643> Stonk Machine",
        "StonkMachineReminder",
        "Get a reminder to lose some coins from stonk investment.",
        True,
    ),
    (
        "rustymachine",
        "<a:RustyMachine:1507484187580432494> Rusty Machine",
        "RustyMachineReminder",
        "Get a reminder to put seeds in. Receive an object, probably.",
        True,
    ),
    (
        "d20",
        "<a:SunbearD20:1507484242148327554> Sunbear's D20",
        "SunbearD20Reminder",
        "Get a reminder to roll a d20.",
        True,
    ),
    (
        "tipjar",
        "<:TipJar:1507484255570100346> Tip Jar",
        "TipJarReminder",
        "Get a reminder to check for some tips.",
        True,
    ),
]


REMINDER_ALIASES = {
    "tipjar": "items",
    "tip_jar": "items",
    "tip_jar_reminder": "items",
    "d20": "items",
    "sunbear_d20": "items",
    "sunbears_d20": "items",
    "stonkmachine": "items",
    "stonk_machine": "items",
    "stonksmachine": "items",
    "stonks_machine": "items",
    "stonk_machine_reminder": "items",
    "rustymachine": "items",
    "rusty_machine": "items",
    "rusty_machine_reminder": "items",
    "rusty": "items",
    "instantcrafting": "items",
    "instant_crafting": "items",
    "instant-finish-crafts": "items",
    "instantfarming": "items",
    "instant_farming": "items",
    "instant-grow-plants": "items",
    "omegabait": "items",
    "omega_bait": "items",
    "omega-bait": "items",
    "item": "items",
    "items_reminder": "items",
    "item_reminders": "items",
    "cmd": "tidy",
    "cmds": "tidy",
    "cmd_reminder": "tidy",
    "cmd_reminders": "tidy",
    "command_reminder": "tidy",
    "command_reminders": "tidy",
    "tidy_reminder": "tidy",
    "dig_reminder": "dig",
    "hunt_reminder": "hunt",
    "workshift": "work_shift",
    "work": "work_shift",
    "pet_activity": "pets_activity",
    "pets": "pets_activity",
    "fishboosts": "fish_boosts",
    "fish_boost": "fish_boosts",
    "fish_boosts_reminder": "fish_boosts",
    "fishboostsreminder": "fish_boosts",
    "summon": "summon_npc",
    "summon_npc": "summon_npc",
    "npc_summon": "summon_npc",
    "npcsummon": "summon_npc",
    "summonnpc": "summon_npc",
    "summon_npc_reminder": "summon_npc",
    "npc_summon_reminder": "summon_npc",
    "npcsummonreminder": "summon_npc",
}

ITEM_ALIASES = {
    "tip_jar": "tipjar",
    "tip_jar_reminder": "tipjar",
    "sunbear_d20": "d20",
    "sunbear_d_20": "d20",
    "sunbears_d20": "d20",
    "sunbears_d_20": "d20",
    "sunbear": "d20",
    "d_20": "d20",
    "stonk_machine": "stonkmachine",
    "stonksmachine": "stonkmachine",
    "stonks_machine": "stonkmachine",
    "stonk_machine_reminder": "stonkmachine",
    "stonk": "stonkmachine",
    "rusty_machine": "rustymachine",
    "rusty_machine_reminder": "rustymachine",
    "rusty": "rustymachine",
    "instant_crafting": "instantcrafting",
    "instant-finish-crafts": "instantcrafting",
    "crafting": "instantcrafting",
    "instant_farming": "instantfarming",
    "instant-grow-plants": "instantfarming",
    "farming": "instantfarming",
    "omega_bait": "omegabait",
    "omega-bait": "omegabait",
}

ASSISTANT_ALIASES = {
    "workshift": "work_shift",
    "work": "work_shift",
    "pets_minigame": "pet_minigame",
    "pet_minigames": "pet_minigame",
    "pets_care": "pet_minigame",
    "pet_care": "pet_minigame",
    "marketassistant": "market_assistant",
    "marketassist": "market_assistant",
    "market_assist": "market_assistant",
    "market": "market_assistant",
    "mpa": "market_assistant",
    "lootboxassistant": "lootbox_assistant",
    "lootbox_assist": "lootbox_assistant",
    "lootboxassist": "lootbox_assistant",
    "lootbox_assistant": "lootbox_assistant",
    "lootbox": "lootbox_assistant",
    "loot_box": "lootbox_assistant",
    "lba": "lootbox_assistant",
}

SettingKind = Literal["reminder", "assistant"]


class NebulaReminderCore(commands.Cog):
    """Shared Components V2 settings hub for Nebula user settings."""

    __author__ = "Nebula"
    __version__ = "2.7.1"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.config = Config.get_conf(
            self,
            identifier=1498458217000000001,
            force_registration=True,
        )

        self.config.register_user(
            reminder_prefs={},
            assistant_prefs={},
            item_prefs={},
            reminder_posts={},
            marriage_mode=None,
        )

        self.discord_write_interval = 0.45
        self._discord_write_lock = asyncio.Lock()
        self._next_discord_write_at = 0.0


    async def discord_write(self, route: Route, **kwargs: Any) -> Any:
        """Paced Discord write helper for reminder engines.

        This is intentionally used for normal channel message creates and deletes.
        Interaction callbacks stay direct so settings buttons can acknowledge quickly.
        """
        async with self._discord_write_lock:
            now = self.bot.loop.time()
            delay = self._next_discord_write_at - now

            if delay > 0:
                await asyncio.sleep(delay)

            try:
                return await self.bot.http.request(route, **kwargs)
            finally:
                self._next_discord_write_at = self.bot.loop.time() + self.discord_write_interval

    def _simple_v2_payload(
        self,
        content: str,
        *,
        mention_user_id: int | None = None,
    ) -> dict[str, Any]:
        components: list[dict[str, Any]] = [
            {
                "type": 17,
                "accent_color": None,
                "spoiler": False,
                "components": [
                    {
                        "type": 10,
                        "content": str(content),
                    }
                ],
            }
        ]

        payload: dict[str, Any] = {
            "flags": IS_COMPONENTS_V2,
            "components": components,
            "allowed_mentions": {
                "parse": [],
            },
        }

        if mention_user_id is not None:
            payload["allowed_mentions"]["users"] = [str(int(mention_user_id))]

        return payload

    async def send_v2_message(
        self,
        channel_id: int,
        content: str,
        *,
        reference_message_id: int | None = None,
        reference_guild_id: int | None = None,
        mention_user_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        data = dict(payload) if isinstance(payload, dict) else self._simple_v2_payload(
            content,
            mention_user_id=mention_user_id,
        )

        if reference_message_id is not None:
            data["message_reference"] = {
                "message_id": int(reference_message_id),
                "channel_id": int(channel_id),
                "fail_if_not_exists": False,
            }

            if reference_guild_id is not None:
                data["message_reference"]["guild_id"] = int(reference_guild_id)

        created = await self.discord_write(
            Route("POST", "/channels/{channel_id}/messages", channel_id=int(channel_id)),
            json=data,
        )

        return int(created["id"])

    async def delete_message(self, channel_id: int, message_id: int) -> bool:
        try:
            await self.discord_write(
                Route(
                    "DELETE",
                    "/channels/{channel_id}/messages/{message_id}",
                    channel_id=int(channel_id),
                    message_id=int(message_id),
                )
            )
            return True
        except discord.NotFound:
            return False
        except discord.Forbidden:
            log.warning(
                "Missing permission to delete reminder message %s in channel %s",
                message_id,
                channel_id,
            )
            return False
        except discord.HTTPException:
            log.exception(
                "Failed to delete reminder message %s in channel %s",
                message_id,
                channel_id,
            )
            return False

    def _normalize_post_key(self, key: str) -> str:
        key = str(key or "").strip().lower()
        return self._normalize_item_key(key)

    async def get_reminder_post(self, user_id: int, key: str) -> dict[str, int] | None:
        key = self._normalize_post_key(key)
        posts = await self.config.user_from_id(int(user_id)).reminder_posts()

        if not isinstance(posts, dict):
            return None

        post = posts.get(key)
        if not isinstance(post, dict):
            return None

        channel_id = self._int_or_none(post.get("channel_id"))
        message_id = self._int_or_none(post.get("message_id"))

        if not channel_id or not message_id:
            return None

        return {
            "channel_id": channel_id,
            "message_id": message_id,
        }

    async def store_reminder_post(
        self,
        user_id: int,
        key: str,
        channel_id: int,
        message_id: int,
    ) -> None:
        key = self._normalize_post_key(key)
        async with self.config.user_from_id(int(user_id)).reminder_posts() as posts:
            posts[key] = {
                "channel_id": int(channel_id),
                "message_id": int(message_id),
            }

    async def clear_reminder_post(self, user_id: int, key: str) -> None:
        key = self._normalize_post_key(key)
        async with self.config.user_from_id(int(user_id)).reminder_posts() as posts:
            posts.pop(key, None)

    async def delete_tracked_reminder_post(self, user_id: int, key: str) -> bool:
        key = self._normalize_post_key(key)
        post = await self.get_reminder_post(user_id, key)

        if post is None:
            await self.clear_reminder_post(user_id, key)
            return False

        deleted = await self.delete_message(post["channel_id"], post["message_id"])
        await self.clear_reminder_post(user_id, key)
        return deleted

    async def replace_reminder_post(
        self,
        user_id: int,
        key: str,
        channel_id: int,
        content: str,
        *,
        reference_message_id: int | None = None,
        reference_guild_id: int | None = None,
        mention_user_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        await self.delete_tracked_reminder_post(user_id, key)
        message_id = await self.send_v2_message(
            channel_id,
            content,
            reference_message_id=reference_message_id,
            reference_guild_id=reference_guild_id,
            mention_user_id=mention_user_id,
            payload=payload,
        )
        await self.store_reminder_post(user_id, key, channel_id, message_id)
        return message_id

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_reminder_key(self, key: str) -> str:
        key = str(key or "").strip().lower()
        return REMINDER_ALIASES.get(key, key)

    def _normalize_item_key(self, key: str) -> str:
        key = str(key or "").strip().lower()
        return ITEM_ALIASES.get(key, key)

    def _normalize_assistant_key(self, key: str) -> str:
        key = str(key or "").strip().lower()
        return ASSISTANT_ALIASES.get(key, key)

    def _valid_cmd_reminder_keys(self) -> set[str]:
        return {k for k, _label, _slash, _description, _premium, _normal in CMD_REMINDER_SETTINGS}

    def _valid_reminder_keys(self) -> set[str]:
        return {k for k, _, _, _ in REMINDER_SETTINGS} | self._valid_cmd_reminder_keys()

    def _ordered_reminder_keys(self) -> list[str]:
        keys = [k for k, _, _, _ in REMINDER_SETTINGS]

        for key, _label, _slash, _description, _premium, _normal in CMD_REMINDER_SETTINGS:
            if key not in keys:
                keys.append(key)

        return keys

    def _valid_assistant_keys(self) -> set[str]:
        return {k for k, _, _, _ in ASSISTANT_SETTINGS}

    def _valid_item_keys(self) -> set[str]:
        return {k for k, _, _, _, _ in ITEM_REMINDER_SETTINGS}

    def _item_default_enabled(self, key: str) -> bool:
        key = self._normalize_item_key(key)

        for item_key, _label, _cog_name, _description, default_enabled in ITEM_REMINDER_SETTINGS:
            if item_key == key:
                return bool(default_enabled)

        return False

    async def is_reminder_enabled(self, user_id: int, key: str) -> bool:
        raw_key = str(key or "").strip().lower()
        item_key = self._normalize_item_key(raw_key)

        if item_key in self._valid_item_keys():
            return await self.is_item_reminder_enabled(user_id, item_key)

        key = self._normalize_reminder_key(raw_key)

        if key not in self._valid_reminder_keys():
            return False

        prefs = await self.config.user_from_id(int(user_id)).reminder_prefs()
        return bool(prefs.get(key, False))

    async def is_assistant_enabled(self, user_id: int, key: str) -> bool:
        key = self._normalize_assistant_key(key)

        if key not in self._valid_assistant_keys():
            return False

        prefs = await self.config.user_from_id(int(user_id)).assistant_prefs()
        return bool(prefs.get(key, False))

    async def is_market_assistant_enabled(self, user_id: int, key: str = "market_assistant") -> bool:
        return await self.is_assistant_enabled(user_id, key)

    async def get_marriage_mode(self, user_id: int) -> str | None:
        mode = await self.config.user_from_id(int(user_id)).marriage_mode()
        return mode if mode in {"user", "alt"} else None

    async def set_marriage_mode(self, user_id: int, mode: str) -> None:
        mode = str(mode or "").strip().lower()
        if mode not in {"user", "alt"}:
            return
        await self.config.user_from_id(int(user_id)).marriage_mode.set(mode)

    async def is_lootbox_assistant_enabled(self, user_id: int, key: str = "lootbox_assistant") -> bool:
        return await self.is_assistant_enabled(user_id, key)

    async def is_enabled(self, user_id: int, kind: SettingKind, key: str) -> bool:
        if kind == "reminder":
            return await self.is_reminder_enabled(user_id, key)

        if kind == "assistant":
            return await self.is_assistant_enabled(user_id, key)

        return False

    async def is_item_reminder_enabled(self, user_id: int, key: str) -> bool:
        key = self._normalize_item_key(key)

        if key not in self._valid_item_keys():
            return False

        conf = self.config.user_from_id(int(user_id))
        prefs = await conf.item_prefs()
        if isinstance(prefs, dict) and key in prefs:
            return bool(prefs.get(key, False))

        reminder_prefs = await conf.reminder_prefs()
        legacy_master_enabled = bool(
            reminder_prefs.get("items", False)
            if isinstance(reminder_prefs, dict)
            else False
        )
        return bool(legacy_master_enabled and self._item_default_enabled(key))

    async def set_enabled(
        self,
        user_id: int,
        kind: SettingKind,
        key: str,
        enabled: bool,
    ) -> None:
        conf = self.config.user_from_id(int(user_id))

        if kind == "reminder":
            raw_key = str(key or "").strip().lower()
            item_key = self._normalize_item_key(raw_key)

            if item_key in self._valid_item_keys():
                await self.set_item_reminder_enabled(user_id, item_key, enabled)
                return

            key = self._normalize_reminder_key(raw_key)
            if key not in self._valid_reminder_keys():
                return

            async with conf.reminder_prefs() as prefs:
                prefs[key] = bool(enabled)
            return

        if kind == "assistant":
            key = self._normalize_assistant_key(key)
            if key not in self._valid_assistant_keys():
                return

            async with conf.assistant_prefs() as prefs:
                prefs[key] = bool(enabled)
            return

    async def set_assistant_enabled(self, user_id: int, key: str, enabled: bool) -> None:
        await self.set_enabled(user_id, "assistant", key, enabled)

    async def set_item_reminder_enabled(self, user_id: int, key: str, enabled: bool) -> None:
        key = self._normalize_item_key(key)

        if key not in self._valid_item_keys():
            return

        async with self.config.user_from_id(int(user_id)).item_prefs() as prefs:
            prefs[key] = bool(enabled)

    async def set_all_item_reminders_enabled(self, user_id: int, enabled: bool) -> None:
        async with self.config.user_from_id(int(user_id)).item_prefs() as prefs:
            for key, _label, _cog_name, _description, _default_enabled in ITEM_REMINDER_SETTINGS:
                prefs[key] = bool(enabled)

    async def toggle_enabled(self, user_id: int, kind: SettingKind, key: str) -> bool:
        if kind == "reminder":
            current = await self.is_reminder_enabled(user_id, key)
        else:
            current = await self.is_assistant_enabled(user_id, key)

        new_value = not current
        await self.set_enabled(user_id, kind, key, new_value)
        return new_value

    async def toggle_item_reminder_enabled(self, user_id: int, key: str) -> bool:
        key = self._normalize_item_key(key)

        if key not in self._valid_item_keys():
            return False

        current = await self.is_item_reminder_enabled(user_id, key)
        new_value = not current
        await self.set_item_reminder_enabled(user_id, key, new_value)
        return new_value

    async def get_prefs(self, user_id: int) -> dict[str, dict[str, bool]]:
        conf = self.config.user_from_id(int(user_id))
        reminder = await conf.reminder_prefs()
        assistant = await conf.assistant_prefs()
        item = await conf.item_prefs()

        reminder = reminder if isinstance(reminder, dict) else {}
        assistant = assistant if isinstance(assistant, dict) else {}
        item = item if isinstance(item, dict) else {}

        legacy_items_enabled = bool(reminder.get("items", False))
        item_effective: dict[str, bool] = {}

        for key, _label, _cog_name, _description, _default_enabled in ITEM_REMINDER_SETTINGS:
            if key in item:
                item_effective[key] = bool(item.get(key, False))
            else:
                item_effective[key] = bool(legacy_items_enabled and self._item_default_enabled(key))

        return {
            "reminder": {
                key: bool(reminder.get(key, False))
                for key in self._ordered_reminder_keys()
            },
            "assistant": {
                key: bool(assistant.get(key, False))
                for key, _, _, _ in ASSISTANT_SETTINGS
            },
            "item": item_effective,
        }

    @commands.hybrid_group(name="settings", invoke_without_command=True)
    async def settings(self, ctx: commands.Context):
        """Open Nebula settings."""
        await self._send_settings_hint(ctx)

    @settings.command(name="user")
    async def settings_user(self, ctx: commands.Context):
        """Open your Nebula user settings."""
        await self._send_user_menu_for_ctx(ctx, page=0)

    async def _send_settings_hint(self, ctx: commands.Context) -> None:
        if ctx.interaction:
            await self._safe_ephemeral(ctx.interaction, "Use `/settings user` to configure your settings.")
            return

        await ctx.reply("Use `/settings user` to configure your settings.", mention_author=False)

    async def _send_user_menu_for_ctx(self, ctx: commands.Context, *, page: int) -> None:
        payload = await self.render_menu(ctx.author.id, page)

        if ctx.interaction:
            try:
                await self._send_interaction_payload(
                    ctx.interaction,
                    payload,
                    ephemeral=False,
                )
            except Exception as exc:
                log.exception("Failed to send settings menu")
                await self._safe_ephemeral(
                    ctx.interaction,
                    f"Could not open settings: `{exc}`",
                )
            return

        await ctx.reply("Use `/settings user` to configure your settings.", mention_author=False)

    async def render_menu(self, user_id: int, page: int) -> dict[str, Any]:
        page = max(0, min(PAGE_COUNT - 1, int(page or 0)))
        rows = await self._settings_for_page(user_id, page)

        children: list[dict[str, Any]] = [
            {
                "type": 10,
                "content": "### Settings",
            },
            {
                "type": 14,
                "divider": True,
                "spacing": 1,
            },
        ]

        children.extend(rows)
        children.extend(
            [
                {
                    "type": 14,
                    "divider": True,
                    "spacing": 1,
                },
                {
                    "type": 10,
                    "content": f"-# Page {page + 1} of {PAGE_COUNT}",
                },
                self._nav_row(page, user_id),
            ]
        )

        return {
            "attachments": [],
            "flags": IS_COMPONENTS_V2,
            "components": [
                {
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": children,
                }
            ],
        }

    async def _settings_for_page(self, user_id: int, page: int) -> list[dict[str, Any]]:
        if page == 0:
            return await self._render_page_one_settings_page(user_id)

        if page == 1:
            return await self._render_page_two_settings_page(user_id)

        if page == 2:
            return await self._render_page_three_settings_page(user_id)

        if page == 3:
            return await self._render_page_four_settings_page(user_id)

        return await self._render_page_five_settings_page(user_id)

    async def _render_page_one_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        prefs = await self.get_prefs(user_id)
        rows: list[dict[str, Any]] = []

        rows.extend(
            self._group_row(
                title="Adventure Reminder・Assistant",
                description="Adventure reminders and helper guide.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["adventure"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:adventure",
                    ),
                    self._toggle_button(
                        enabled=prefs["assistant"]["adventure"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:adventure",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Pets Activity Reminder・Pets Care Assistant",
                description="Pets activity reminders and pets care helper prompts.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["pets_activity"],
                        label_on="Activity On",
                        label_off="Activity Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:pets_activity",
                    ),
                    self._toggle_button(
                        enabled=prefs["assistant"]["pet_minigame"],
                        label_on="Care On",
                        label_off="Care Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:pet_minigame",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Work Shift Reminder・Assistant",
                description="Reminder and helper prompt for work shift.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["work_shift"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:work_shift",
                    ),
                    self._toggle_button(
                        enabled=prefs["assistant"]["work_shift"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:work_shift",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Collector Rewards Reminder",
                description="Reminder when collector rewards can be claimed again.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["collector_rewards"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:collector_rewards",
                    ),
                ],
            )
        )
        return rows

    async def _render_page_two_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        prefs = await self.get_prefs(user_id)
        marriage_mode = await self.get_marriage_mode(user_id)
        rows: list[dict[str, Any]] = []

        rows.extend(
            self._group_row(
                title="Farm Reminder",
                description="Reminder when crops are ready to harvest.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["farm"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:farm",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Fish Boosts Reminder",
                description="Reminder when fish boosts rotate.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["fish_boosts"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:fish_boosts",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Giveaway Reminder",
                description="Reminder when giveaway create is ready again.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["giveaway"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:giveaway",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Marriage Upkeep Reminder",
                description="Reminder when marriage upkeep needs attention.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["marriage"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:marriage",
                    ),
                    {
                        "type": 2,
                        "style": 3 if marriage_mode == "user" else 2,
                        "label": f"{'✓ ' if marriage_mode == 'user' else ''}User Account",
                        "custom_id": f"nebset:{user_id}:marriagemode:user",
                    },
                    {
                        "type": 2,
                        "style": 3 if marriage_mode == "alt" else 2,
                        "label": f"{'✓ ' if marriage_mode == 'alt' else ''}Alt Account",
                        "custom_id": f"nebset:{user_id}:marriagemode:alt",
                    },
                ],
            )
        )

        return rows

    async def _render_page_three_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        prefs = await self.get_prefs(user_id)
        rows: list[dict[str, Any]] = []

        rows.extend(
            self._group_row(
                title="Scratch Reminder",
                description="Reminder when scratch is available again.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["scratch"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:scratch",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Stream Reminder",
                description="Stream interaction reminders and ending warnings.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["stream"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:stream",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Summon NPC Reminder",
                description="Reminder when NPC summon is ready again.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["reminder"]["summon_npc"],
                        label_on="Reminder On",
                        label_off="Reminder Off",
                        custom_id=f"nebset:{user_id}:toggle:reminder:summon_npc",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Loot Box Assistant",
                description="Net profit helper prompts for loot box openings.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["assistant"]["lootbox_assistant"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:lootbox_assistant",
                    ),
                ],
            )
        )

        return rows

    async def _render_page_four_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        prefs = await self.get_prefs(user_id)
        rows: list[dict[str, Any]] = []

        rows.extend(
            self._group_row(
                title="Market Assistant",
                description="Value and gain helpers for Dank Memer market view listings.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["assistant"]["market_assistant"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:market_assistant",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="NPC Interaction Assistant",
                description="Helper prompts for NPC interactions.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["assistant"]["npc_interaction"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:npc_interaction",
                    ),
                ],
            )
        )

        rows.extend(
            self._group_row(
                title="Trivia Assistant",
                description="Helper prompts for trivia questions.",
                buttons=[
                    self._toggle_button(
                        enabled=prefs["assistant"]["trivia"],
                        label_on="Assistant On",
                        label_off="Assistant Off",
                        custom_id=f"nebset:{user_id}:toggle:assistant:trivia",
                    ),
                ],
            )
        )

        rows.extend(await self._claim_group_row(user_id))
        return rows

    async def _render_page_five_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        prefs = await self.get_prefs(user_id)
        rows: list[dict[str, Any]] = []
        rows.extend(await self._cmd_group_row(user_id, prefs))
        rows.extend(await self._item_group_row(user_id, prefs))
        return rows

    async def _render_main_settings_page(self, user_id: int) -> list[dict[str, Any]]:
        return await self._render_page_one_settings_page(user_id)

    async def _render_more_reminders_page(self, user_id: int) -> list[dict[str, Any]]:
        return await self._render_page_two_settings_page(user_id)

    async def _render_other_assistants_page(self, user_id: int) -> list[dict[str, Any]]:
        return await self._render_page_four_settings_page(user_id)

    async def _cmd_group_row(
        self,
        user_id: int,
        prefs: dict[str, dict[str, bool]],
    ) -> list[dict[str, Any]]:
        enabled_count = sum(
            1
            for key, _label, _slash, _description, _premium, _normal in CMD_REMINDER_SETTINGS
            if prefs["reminder"].get(key, False)
        )
        total = len(CMD_REMINDER_SETTINGS)

        return self._group_row(
            title="CMD Reminders",
            description=f"Command cooldown reminders. Enabled: {enabled_count}/{total}.",
            buttons=[
                self._neutral_button(
                    label="Configure",
                    custom_id=f"nebset:{user_id}:cmdcfg:open",
                ),
            ],
        )

    async def _tidy_group_row(
        self,
        user_id: int,
        prefs: dict[str, dict[str, bool]],
    ) -> list[dict[str, Any]]:
        return await self._cmd_group_row(user_id, prefs)

    async def _item_group_row(
        self,
        user_id: int,
        prefs: dict[str, dict[str, bool]],
    ) -> list[dict[str, Any]]:
        enabled_count = 0

        for key, _label, _cog_name, _description, _default_enabled in ITEM_REMINDER_SETTINGS:
            if prefs["item"].get(key, False):
                enabled_count += 1

        total = len(ITEM_REMINDER_SETTINGS)

        return self._group_row(
            title="Item Reminders",
            description=f"Item usage reminders. Enabled: {enabled_count}/{total}.",
            buttons=[
                self._neutral_button(
                    label="Configure",
                    custom_id=f"nebset:{user_id}:itemcfg:open",
                ),
            ],
        )

    async def _claim_group_row(self, user_id: int) -> list[dict[str, Any]]:
        claimtracker = self.bot.get_cog("ClaimReminder")
        status = None

        if claimtracker is not None:
            getter = getattr(claimtracker, "get_status", None)
            if getter is not None:
                with contextlib.suppress(Exception):
                    status = await getter(user_id)

        enabled_count = 0

        if isinstance(status, dict):
            for key, _label, _description in CLAIM_SETTINGS:
                row_status = status.get(key)
                if isinstance(row_status, dict) and row_status.get("enabled", False):
                    enabled_count += 1

        return self._group_row(
            title="Claim Reminders",
            description=f"Daily, weekly, and monthly claim reminders. Enabled: {enabled_count}/3.",
            buttons=[
                self._neutral_button(
                    label="Configure",
                    custom_id=f"nebset:{user_id}:claimcfg:open",
                    disabled=claimtracker is None,
                ),
            ],
        )

    def _group_row(
        self,
        *,
        title: str,
        description: str,
        buttons: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": 10,
                "content": f"**{title}**\n-# {description}",
            },
            {
                "type": 1,
                "components": buttons,
            },
        ]

    def _toggle_button(
        self,
        *,
        enabled: bool,
        label_on: str,
        label_off: str,
        custom_id: str,
        disabled: bool = False,
    ) -> dict[str, Any]:
        return {
            "type": 2,
            "style": 3 if enabled else 4,
            "label": label_on if enabled else label_off,
            "custom_id": custom_id,
            "disabled": bool(disabled),
        }

    def _neutral_button(
        self,
        *,
        label: str,
        custom_id: str,
        disabled: bool = False,
    ) -> dict[str, Any]:
        return {
            "type": 2,
            "style": 2,
            "label": label,
            "custom_id": custom_id,
            "disabled": bool(disabled),
        }

    def _setting_row(
        self,
        *,
        label: str,
        description: str,
        enabled: bool,
        custom_id: str,
        disabled: bool = False,
    ) -> dict[str, Any]:
        return {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": f"**{label}**\n-# {description}",
                }
            ],
            "accessory": {
                "type": 2,
                "style": 3 if enabled else 4,
                "label": "On" if enabled else "Off",
                "custom_id": custom_id,
                "disabled": bool(disabled),
            },
        }

    def _nav_row(self, page: int, owner_id: int) -> dict[str, Any]:
        return {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "emoji": {
                        "id": ARROW_LEFT_LEFT_ID,
                        "name": "leftleft",
                        "animated": False,
                    },
                    "custom_id": f"nebset:{owner_id}:page:first:0",
                    "disabled": page == 0,
                },
                {
                    "type": 2,
                    "style": 2,
                    "emoji": {
                        "id": ARROW_LEFT_ID,
                        "name": "ArrowLeftui",
                        "animated": False,
                    },
                    "custom_id": f"nebset:{owner_id}:page:prev:{max(0, page - 1)}",
                    "disabled": page == 0,
                },
                {
                    "type": 2,
                    "style": 2,
                    "emoji": {
                        "id": REFRESH_ID,
                        "name": "Refreshui",
                        "animated": False,
                    },
                    "custom_id": f"nebset:{owner_id}:refresh:{page}",
                },
                {
                    "type": 2,
                    "style": 2,
                    "emoji": {
                        "id": ARROW_RIGHT_ID,
                        "name": "ArrowRightui",
                        "animated": False,
                    },
                    "custom_id": f"nebset:{owner_id}:page:next:{min(PAGE_COUNT - 1, page + 1)}",
                    "disabled": page >= PAGE_COUNT - 1,
                },
                {
                    "type": 2,
                    "style": 2,
                    "emoji": {
                        "id": ARROW_RIGHT_RIGHT_ID,
                        "name": "rightright",
                        "animated": False,
                    },
                    "custom_id": f"nebset:{owner_id}:page:last:{PAGE_COUNT - 1}",
                    "disabled": page >= PAGE_COUNT - 1,
                },
            ],
        }

    def _page_for_setting(self, kind: str, key: str) -> int:
        if kind == "claim":
            return 3

        if kind == "item":
            return 4

        if kind == "assistant":
            key = self._normalize_assistant_key(key)
            if key in {"adventure", "work_shift", "pet_minigame"}:
                return 0
            if key == "lootbox_assistant":
                return 2
            if key in {"market_assistant", "npc_interaction", "trivia"}:
                return 3

        if kind == "reminder":
            key = self._normalize_reminder_key(key)
            if key in {"adventure", "work_shift", "pets_activity", "collector_rewards"}:
                return 0
            if key in {"farm", "fish_boosts", "giveaway", "marriage"}:
                return 1
            if key in {"scratch", "stream", "summon_npc"}:
                return 2
            if key == "items" or key in self._valid_cmd_reminder_keys():
                return 4

        return 0

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        data = interaction.data or {}
        custom_id = str(data.get("custom_id") or "")

        if not custom_id.startswith("nebset:"):
            return

        parsed = self._parse_nebset_custom_id(custom_id, interaction.user.id)
        if parsed is None:
            await self._safe_ephemeral(interaction, "Invalid settings button.")
            return

        owner_id, action, rest = parsed

        if owner_id != interaction.user.id:
            await self._safe_ephemeral(interaction, "This settings panel belongs to someone else.")
            return

        if action == "close":
            await self._handle_close(interaction)
            return

        if action == "refresh":
            await self._handle_refresh(interaction, owner_id, rest)
            return

        if action == "page":
            await self._handle_page(interaction, owner_id, rest)
            return

        if action == "toggle":
            await self._handle_toggle(interaction, owner_id, rest)
            return

        if action == "marriagemode":
            await self._handle_marriage_mode(interaction, owner_id, rest)
            return

        if action == "tidycd":
            await self._handle_tidy_cooldown(interaction, owner_id, rest)
            return

        if action == "cmdcfg":
            await self._handle_cmd_config(interaction, owner_id, rest)
            return

        if action == "togglecmd":
            await self._handle_cmd_toggle(interaction, owner_id, rest)
            return

        if action == "cmdcd":
            await self._handle_cmd_cooldown(interaction, owner_id, rest)
            return

        if action == "itemcfg":
            await self._handle_item_config(interaction, owner_id, rest)
            return

        if action == "toggleitem":
            await self._handle_item_toggle(interaction, owner_id, rest)
            return

        if action == "claimcfg":
            await self._handle_claim_config(interaction, owner_id, rest)
            return

        if action == "route":
            await self._handle_claim_route(interaction, owner_id, rest)
            return

    def _parse_nebset_custom_id(
        self,
        custom_id: str,
        fallback_owner_id: int,
    ) -> tuple[int, str, list[str]] | None:
        parts = custom_id.split(":")

        if len(parts) < 2 or parts[0] != "nebset":
            return None

        if len(parts) >= 3 and parts[1].isdigit():
            return int(parts[1]), parts[2], parts[3:]

        return int(fallback_owner_id), parts[1], parts[2:]

    async def _handle_marriage_mode(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        if len(parts) != 1 or parts[0] not in {"user", "alt"}:
            await self._safe_ephemeral(interaction, "Invalid marriage account option.")
            return

        mode = parts[0]
        await self.set_marriage_mode(owner_id, mode)
        await self.set_enabled(owner_id, "reminder", "marriage", True)
        await self._sync_reminder_engine(owner_id, "marriage", True)
        await self._edit_interaction_menu(interaction, owner_id, 1)
        await self._begin_marriage_setup(owner_id, mode, interaction.channel_id)

    async def _begin_marriage_setup(
        self,
        user_id: int,
        mode: str,
        channel_id: int | None,
    ) -> None:
        if channel_id is None:
            return

        cog = self.bot.get_cog("MarriageReminder")
        setter = getattr(cog, "set_marriage_mode", None) if cog is not None else None
        if setter is None:
            return

        try:
            await setter(int(user_id), mode, channel_id=int(channel_id))
        except Exception:
            log.exception("Failed to start marriage setup for user %s", user_id)

    async def _handle_toggle(self, interaction: discord.Interaction, owner_id: int, parts: list[str]) -> None:
        if len(parts) != 2:
            await self._safe_ephemeral(interaction, "Invalid toggle button.")
            return

        kind_raw, key = parts

        if kind_raw == "claim":
            await self._toggle_claim(interaction, owner_id, key)
            return

        if kind_raw not in {"reminder", "assistant"}:
            await self._safe_ephemeral(interaction, "Invalid toggle type.")
            return

        kind: SettingKind = "reminder" if kind_raw == "reminder" else "assistant"
        new_value = await self.toggle_enabled(owner_id, kind, key)

        if kind == "reminder":
            normalized_key = self._normalize_reminder_key(key)

            if normalized_key == "items":
                await self.set_all_item_reminders_enabled(owner_id, new_value)
                await self._sync_item_engines(owner_id)
            else:
                await self._sync_reminder_engine(owner_id, normalized_key, new_value)

        if kind == "assistant":
            await self._sync_assistant_engine(owner_id, key, new_value)

        page = self._page_for_setting(kind, key)
        await self._edit_interaction_menu(interaction, owner_id, page)

        if kind == "reminder" and normalized_key == "marriage" and new_value:
            mode = await self.get_marriage_mode(owner_id)
            if mode is not None:
                await self._begin_marriage_setup(owner_id, mode, interaction.channel_id)

    async def _handle_tidy_cooldown(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        await self._handle_cmd_cooldown(interaction, owner_id, ["toggle", "tidy"])

    async def _handle_cmd_config(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        await self._edit_cmd_config_menu(interaction, owner_id)

    async def _handle_cmd_toggle(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        if len(parts) != 1:
            await self._safe_ephemeral(interaction, "Invalid command reminder button.")
            return

        key = self._normalize_reminder_key(parts[0])
        if key not in self._valid_cmd_reminder_keys():
            await self._safe_ephemeral(interaction, "Unknown command reminder.")
            return

        new_value = await self.toggle_enabled(owner_id, "reminder", key)
        await self._sync_cmd_reminder_engine(owner_id, key, new_value)
        await self._edit_cmd_config_menu(interaction, owner_id)

    async def _handle_cmd_cooldown(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        if len(parts) == 1:
            key = self._normalize_reminder_key(parts[0])
        elif len(parts) == 2 and parts[0] == "toggle":
            key = self._normalize_reminder_key(parts[1])
        else:
            await self._safe_ephemeral(interaction, "Invalid command cooldown button.")
            return

        spec = self._cmd_spec(key)
        if spec is None:
            await self._safe_ephemeral(interaction, "Unknown command reminder.")
            return

        current = await self._get_cmd_cooldown(owner_id, key)
        new_cooldown = spec[5] if current == spec[4] else spec[4]

        changed = await self._set_cmd_cooldown(owner_id, key, new_cooldown)
        if not changed:
            await self._safe_ephemeral(interaction, "CmdReminder cooldown settings are not available.")

        await self._edit_cmd_config_menu(interaction, owner_id)

    async def _handle_item_config(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        await self._edit_item_config_menu(interaction, owner_id)

    async def _handle_item_toggle(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        if len(parts) != 1:
            await self._safe_ephemeral(interaction, "Invalid item reminder button.")
            return

        key = self._normalize_item_key(parts[0])
        await self.toggle_item_reminder_enabled(owner_id, key)
        await self._sync_item_engine(owner_id, key)
        await self._edit_item_config_menu(interaction, owner_id)

    async def _handle_claim_config(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        parts: list[str],
    ) -> None:
        await self._edit_claim_config_menu(interaction, owner_id)

    async def _sync_assistant_engine(self, user_id: int, key: str, enabled: bool) -> None:
        key = self._normalize_assistant_key(key)

        for setting_key, _label, cog_name, _description in ASSISTANT_SETTINGS:
            if setting_key != key:
                continue

            await self._call_engine_enabled(cog_name, user_id, enabled)
            return

    async def _sync_reminder_engine(self, user_id: int, key: str, enabled: bool) -> None:
        key = self._normalize_reminder_key(key)

        if key in self._valid_cmd_reminder_keys():
            await self._sync_cmd_reminder_engine(user_id, key, enabled)
            return

        for setting_key, _label, cog_name, _description in REMINDER_SETTINGS:
            if setting_key != key:
                continue

            if cog_name == "ItemReminderGroup":
                await self._sync_item_engines(user_id)
                return

            await self._call_engine_enabled(cog_name, user_id, enabled)
            return

    async def _sync_cmd_reminder_engine(self, user_id: int, key: str, enabled: bool) -> None:
        key = self._normalize_reminder_key(key)
        if key not in self._valid_cmd_reminder_keys():
            return

        cog = self.bot.get_cog("CmdReminder")
        if cog is not None:
            setter = getattr(cog, "set_reminder_enabled", None)
            if setter is not None:
                try:
                    await setter(int(user_id), key, bool(enabled))
                except Exception:
                    log.exception(
                        "Failed to sync CmdReminder setting for user %s key %s",
                        user_id,
                        key,
                    )
                return

            for setter_name in ("set_user_enabled", "set_enabled"):
                setter = getattr(cog, setter_name, None)
                if setter is None:
                    continue

                try:
                    await setter(int(user_id), bool(enabled), post_key=key)
                except TypeError:
                    if key == "tidy":
                        await setter(int(user_id), bool(enabled))
                except Exception:
                    log.exception(
                        "Failed to sync CmdReminder setting for user %s key %s",
                        user_id,
                        key,
                    )
                return

        if key == "tidy":
            await self._call_engine_enabled("TidyReminder", user_id, enabled)

    async def _sync_item_engines(self, user_id: int) -> None:
        for key, _label, _cog_name, _description, _default_enabled in ITEM_REMINDER_SETTINGS:
            await self._sync_item_engine(user_id, key)

    async def _sync_item_engine(self, user_id: int, key: str) -> None:
        key = self._normalize_item_key(key)
        enabled = await self.is_item_reminder_enabled(user_id, key)

        for item_key, _label, cog_name, _description, _default_enabled in ITEM_REMINDER_SETTINGS:
            if item_key != key:
                continue

            await self._call_engine_enabled(cog_name, user_id, enabled)
            return

    async def _call_engine_enabled(self, cog_name: str, user_id: int, enabled: bool) -> None:
        cog = self.bot.get_cog(cog_name)
        if cog is None:
            return

        for setter_name in ("set_enabled", "set_user_enabled"):
            setter = getattr(cog, setter_name, None)
            if setter is None:
                continue

            try:
                await setter(int(user_id), bool(enabled))
            except Exception:
                log.exception(
                    "Failed to sync setting with %s for user %s",
                    cog_name,
                    user_id,
                )
            return

    async def _toggle_claim(self, interaction: discord.Interaction, owner_id: int, key: str) -> None:
        claimtracker = self.bot.get_cog("ClaimReminder")
        if claimtracker is None:
            await self._safe_ephemeral(interaction, "This setting is not available yet.")
            await self._edit_claim_config_menu(interaction, owner_id)
            return

        getter = getattr(claimtracker, "get_status", None)
        setter = getattr(claimtracker, "set_enabled", None)
        set_route = getattr(claimtracker, "set_route", None)

        if getter is None or setter is None:
            await self._safe_ephemeral(interaction, "This setting is not available yet.")
            await self._edit_claim_config_menu(interaction, owner_id)
            return

        status = await getter(owner_id)
        current = bool((status.get(key) or {}).get("enabled", False))
        new_enabled = not current

        if new_enabled and set_route is not None:
            route = str((status.get(key) or {}).get("route") or "channel")
            if route == "channel" and interaction.channel_id is not None:
                await set_route(owner_id, key, "channel", channel_id=int(interaction.channel_id))

        await setter(owner_id, key, new_enabled)
        await self._edit_claim_config_menu(interaction, owner_id)

    async def _handle_claim_route(self, interaction: discord.Interaction, owner_id: int, parts: list[str]) -> None:
        if len(parts) != 2 or parts[0] != "claim":
            await self._safe_ephemeral(interaction, "Invalid route button.")
            return

        key = parts[1]
        claimtracker = self.bot.get_cog("ClaimReminder")

        if claimtracker is None:
            await self._safe_ephemeral(interaction, "This setting is not available yet.")
            await self._edit_claim_config_menu(interaction, owner_id)
            return

        getter = getattr(claimtracker, "get_status", None)
        set_route = getattr(claimtracker, "set_route", None)

        if getter is None or set_route is None:
            await self._safe_ephemeral(interaction, "This setting is not available yet.")
            await self._edit_claim_config_menu(interaction, owner_id)
            return

        status = await getter(owner_id)
        current_route = str((status.get(key) or {}).get("route") or "channel")
        new_route = "dm" if current_route == "channel" else "channel"

        if new_route == "channel":
            await set_route(
                owner_id,
                key,
                "channel",
                channel_id=int(interaction.channel_id) if interaction.channel_id else None,
            )
        else:
            await set_route(owner_id, key, "dm")

        await self._edit_claim_config_menu(interaction, owner_id)

    async def _handle_page(self, interaction: discord.Interaction, owner_id: int, parts: list[str]) -> None:
        raw_page = parts[-1] if parts else "0"

        try:
            page = int(raw_page)
        except ValueError:
            page = 0

        page = max(0, min(PAGE_COUNT - 1, page))
        await self._edit_interaction_menu(interaction, owner_id, page)

    async def _handle_refresh(self, interaction: discord.Interaction, owner_id: int, parts: list[str]) -> None:
        if parts:
            try:
                page = int(parts[-1])
            except ValueError:
                page = self._page_from_message_payload(interaction.message)
        else:
            page = self._page_from_message_payload(interaction.message)

        page = max(0, min(PAGE_COUNT - 1, page))
        await self._edit_interaction_menu(interaction, owner_id, page)

    async def _handle_close(self, interaction: discord.Interaction) -> None:
        payload = self._closed_payload()
        try:
            await self._edit_interaction_message_payload(interaction, payload)
        except Exception as exc:
            log.exception("Failed to close settings menu")
            await self._safe_ephemeral(interaction, f"Could not close settings: `{exc}`")

    async def _edit_interaction_menu(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        page: int,
    ) -> None:
        payload = await self.render_menu(owner_id, page)

        try:
            await self._edit_interaction_message_payload(interaction, payload)
        except Exception as exc:
            log.exception("Failed to edit settings menu")
            await self._safe_ephemeral(
                interaction,
                f"Could not update settings: `{exc}`",
            )

    async def _edit_cmd_config_menu(
        self,
        interaction: discord.Interaction,
        owner_id: int,
    ) -> None:
        payload = await self.render_cmd_config(owner_id)

        try:
            await self._edit_interaction_message_payload(interaction, payload)
        except Exception as exc:
            log.exception("Failed to edit command reminder config")
            await self._safe_ephemeral(
                interaction,
                f"Could not update command reminders: `{exc}`",
            )

    async def _edit_item_config_menu(
        self,
        interaction: discord.Interaction,
        owner_id: int,
    ) -> None:
        payload = await self.render_item_config(owner_id)

        try:
            await self._edit_interaction_message_payload(interaction, payload)
        except Exception as exc:
            log.exception("Failed to edit item reminder config")
            await self._safe_ephemeral(
                interaction,
                f"Could not update item reminders: `{exc}`",
            )

    async def _edit_claim_config_menu(
        self,
        interaction: discord.Interaction,
        owner_id: int,
    ) -> None:
        payload = await self.render_claim_config(owner_id)

        try:
            await self._edit_interaction_message_payload(interaction, payload)
        except Exception as exc:
            log.exception("Failed to edit claim reminder config")
            await self._safe_ephemeral(
                interaction,
                f"Could not update claim reminders: `{exc}`",
            )

    def _cmd_spec(self, key: str) -> tuple[str, str, str, str, float, float] | None:
        key = self._normalize_reminder_key(key)

        for spec in CMD_REMINDER_SETTINGS:
            if spec[0] == key:
                return spec

        return None

    def _cmd_cog(self, key: str | None = None) -> commands.Cog | None:
        cmd = self.bot.get_cog("CmdReminder")
        if cmd is not None:
            return cmd

        if key is None or self._normalize_reminder_key(key) == "tidy":
            return self.bot.get_cog("TidyReminder")

        return None

    async def _get_cmd_cooldown(self, user_id: int, key: str) -> float:
        key = self._normalize_reminder_key(key)
        spec = self._cmd_spec(key)
        if spec is None:
            return 0.0

        cog = self._cmd_cog(key)
        getter = getattr(cog, "get_user_settings", None) if cog is not None else None
        if getter is not None:
            try:
                settings = await getter(int(user_id), key)
            except TypeError:
                if key != "tidy":
                    settings = None
                else:
                    settings = await getter(int(user_id))
            except Exception:
                log.exception(
                    "Failed to read CmdReminder cooldown for user %s key %s",
                    user_id,
                    key,
                )
                settings = None

            if isinstance(settings, dict):
                raw_cooldown = settings.get("cooldown_seconds")
                with contextlib.suppress(TypeError, ValueError):
                    return float(raw_cooldown)

        return float(spec[4])

    async def _set_cmd_cooldown(self, user_id: int, key: str, cooldown_seconds: float) -> bool:
        key = self._normalize_reminder_key(key)
        cog = self._cmd_cog(key)
        if cog is None:
            return False

        setter = getattr(cog, "set_reminder_cooldown", None)
        if setter is not None:
            try:
                await setter(int(user_id), key, float(cooldown_seconds))
                return True
            except Exception:
                log.exception(
                    "Failed to set CmdReminder cooldown for user %s key %s",
                    user_id,
                    key,
                )
                return False

        setter = getattr(cog, "set_user_cooldown", None)
        if setter is None:
            return False

        try:
            await setter(int(user_id), float(cooldown_seconds), post_key=key)
            return True
        except TypeError:
            if key != "tidy":
                return False
            await setter(int(user_id), float(cooldown_seconds))
            return True
        except Exception:
            log.exception(
                "Failed to set command reminder cooldown for user %s key %s",
                user_id,
                key,
            )
            return False

    def _cmd_mode_label(self, cooldown: float, premium: float, normal: float) -> str:
        if float(cooldown) == float(normal):
            return f"Regular {normal:g}s"

        return f"Premium {premium:g}s"

    async def render_cmd_config(self, user_id: int) -> dict[str, Any]:
        prefs = await self.get_prefs(user_id)
        children: list[dict[str, Any]] = [
            {
                "type": 10,
                "content": "### Settings",
            },
            {
                "type": 14,
                "divider": True,
                "spacing": 1,
            },
        ]

        for key, label, slash, description, premium, normal in CMD_REMINDER_SETTINGS:
            enabled = bool(prefs["reminder"].get(key, False))
            cooldown = await self._get_cmd_cooldown(user_id, key)
            mode_label = self._cmd_mode_label(cooldown, premium, normal)
            cmd_cog = self._cmd_cog(key)

            children.extend(
                self._group_row(
                    title=f"{label} {slash}",
                    description=f"{description} Mode: {mode_label}.",
                    buttons=[
                        self._toggle_button(
                            enabled=enabled,
                            label_on="Reminder On",
                            label_off="Reminder Off",
                            custom_id=f"nebset:{user_id}:togglecmd:{key}",
                        ),
                        self._neutral_button(
                            label=mode_label,
                            custom_id=f"nebset:{user_id}:cmdcd:toggle:{key}",
                            disabled=cmd_cog is None,
                        ),
                    ],
                )
            )

        children.extend(
            [
                {
                    "type": 14,
                    "divider": True,
                    "spacing": 1,
                },
                {
                    "type": 1,
                    "components": [
                        self._neutral_button(
                            label="Back",
                            custom_id=f"nebset:{user_id}:page:back:0",
                        )
                    ],
                },
            ]
        )

        return {
            "attachments": [],
            "flags": IS_COMPONENTS_V2,
            "components": [
                {
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": children,
                }
            ],
        }

    async def render_item_config(self, user_id: int) -> dict[str, Any]:
        prefs = await self.get_prefs(user_id)

        children: list[dict[str, Any]] = [
            {
                "type": 10,
                "content": "### Item Reminders",
            },
            {
                "type": 10,
                "content": "-# Choose which item usage reminders Nebula should track.",
            },
            {
                "type": 14,
                "divider": True,
                "spacing": 1,
            },
        ]

        for key, label, _cog_name, description, _default_enabled in ITEM_REMINDER_SETTINGS:
            enabled = bool(prefs["item"].get(key, False))

            children.append(
                self._setting_row(
                    label=label,
                    description=description,
                    enabled=enabled,
                    custom_id=f"nebset:{user_id}:toggleitem:{key}",
                    disabled=False,
                )
            )

        children.extend(
            [
                {
                    "type": 14,
                    "divider": True,
                    "spacing": 1,
                },
                {
                    "type": 1,
                    "components": [
                        self._neutral_button(
                            label="Back",
                            custom_id=f"nebset:{user_id}:page:back:0",
                        )
                    ],
                },
            ]
        )

        return {
            "attachments": [],
            "flags": IS_COMPONENTS_V2,
            "components": [
                {
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": children,
                }
            ],
        }

    async def render_claim_config(self, user_id: int) -> dict[str, Any]:
        claimtracker = self.bot.get_cog("ClaimReminder")
        status = None

        if claimtracker is not None:
            getter = getattr(claimtracker, "get_status", None)
            if getter is not None:
                with contextlib.suppress(Exception):
                    status = await getter(user_id)

        children: list[dict[str, Any]] = [
            {
                "type": 10,
                "content": "### Claim Reminders",
            },
            {
                "type": 10,
                "content": "-# Choose which claim reminders you want Nebula to track.",
            },
            {
                "type": 14,
                "divider": True,
                "spacing": 1,
            },
        ]

        for key, label, description in CLAIM_SETTINGS:
            row_status = status.get(key) if isinstance(status, dict) else None
            enabled = (
                bool(row_status.get("enabled", False))
                if isinstance(row_status, dict)
                else False
            )

            children.append(
                self._setting_row(
                    label=label,
                    description=description,
                    enabled=enabled,
                    custom_id=f"nebset:{user_id}:toggle:claim:{key}",
                    disabled=claimtracker is None,
                )
            )

        children.extend(
            [
                {
                    "type": 14,
                    "divider": True,
                    "spacing": 1,
                },
                {
                    "type": 1,
                    "components": [
                        self._neutral_button(
                            label="Back",
                            custom_id=f"nebset:{user_id}:page:back:1",
                        )
                    ],
                },
            ]
        )

        return {
            "attachments": [],
            "flags": IS_COMPONENTS_V2,
            "components": [
                {
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": children,
                }
            ],
        }

    def _page_from_message_payload(self, message: discord.Message | None) -> int:
        if message is None:
            return 0

        def walk(node: Any) -> str | None:
            if isinstance(node, dict):
                if node.get("type") == 10:
                    content = node.get("content")
                    if isinstance(content, str) and "Page " in content:
                        return content

                for value in node.values():
                    found = walk(value)
                    if found:
                        return found

            if isinstance(node, list):
                for item in node:
                    found = walk(item)
                    if found:
                        return found

            return None

        try:
            payload = message.to_dict()
        except Exception:
            payload = {}

        found = walk(payload)
        if not found:
            return 0

        match = None
        with contextlib.suppress(Exception):
            import re

            match = re.search(r"Page\s+(\d+)\s+of", found)

        if match:
            return max(0, min(PAGE_COUNT - 1, int(match.group(1)) - 1))

        return 0

    def _closed_payload(self) -> dict[str, Any]:
        return {
            "attachments": [],
            "flags": IS_COMPONENTS_V2,
            "components": [
                {
                    "type": 17,
                    "accent_color": None,
                    "spoiler": False,
                    "components": [
                        {
                            "type": 10,
                            "content": "### User Settings\n-# Closed.",
                        }
                    ],
                }
            ],
        }

    async def _send_interaction_payload(
        self,
        interaction: discord.Interaction,
        payload: dict[str, Any],
        *,
        ephemeral: bool = True,
    ) -> None:
        data = dict(payload or {})

        if ephemeral:
            current_flags = int(data.get("flags") or 0)
            data["flags"] = current_flags | EPHEMERAL

        if interaction.response.is_done():
            await self._send_followup_payload(interaction, data)
            return

        body = {
            "type": 4,
            "data": data,
        }

        route = Route(
            "POST",
            "/interactions/{interaction_id}/{interaction_token}/callback",
            interaction_id=interaction.id,
            interaction_token=interaction.token,
        )
        await self.bot.http.request(route, json=body)

    async def _send_followup_payload(
        self,
        interaction: discord.Interaction,
        payload: dict[str, Any],
    ) -> None:
        route = Route(
            "POST",
            "/webhooks/{application_id}/{interaction_token}",
            application_id=self.bot.application_id,
            interaction_token=interaction.token,
        )
        await self.bot.http.request(route, json=payload)

    async def _edit_interaction_message_payload(
        self,
        interaction: discord.Interaction,
        payload: dict[str, Any],
    ) -> None:
        data = dict(payload or {})

        body = {
            "type": 7,
            "data": data,
        }

        route = Route(
            "POST",
            "/interactions/{interaction_id}/{interaction_token}/callback",
            interaction_id=interaction.id,
            interaction_token=interaction.token,
        )
        await self.bot.http.request(route, json=body)

    async def _safe_ephemeral(self, interaction: discord.Interaction, content: str) -> None:
        with contextlib.suppress(discord.HTTPException):
            if interaction.response.is_done():
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NebulaReminderCore(bot))
