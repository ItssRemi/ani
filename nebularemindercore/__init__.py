from .nebularemindercore import NebulaReminderCore


async def setup(bot):
    await bot.add_cog(NebulaReminderCore(bot))