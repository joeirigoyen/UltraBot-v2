
# Specific imports
from discord.ext import commands

# Custom imports
from log.logger import mLogInfo, mLogError

class Utils(commands.Cog, name='utility'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
        mLogInfo('Dbd cog initialized')

    @commands.Cog.listener()
    async def on_ready(self):
        mLogInfo('Dbd cog is ready')