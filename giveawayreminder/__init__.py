from .giveawayreminder import GiveawayReminder


async def setup(bot):
    await bot.add_cog(GiveawayReminder(bot))
