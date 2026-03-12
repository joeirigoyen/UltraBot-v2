# Specific imports
from discord import app_commands, Interaction, Color, Embed, Message, File
from discord.ext import commands

# Custom imports
from entities.handlers import fun
from entities.handlers.buttons import ResultsButtons
from entities.utils.rare import mCheckIntOrStr, mFindMostSimilarPartial, mListMostSimilarPartial, mBuildEnlistedMessage, mFindMostSimilarJelly
from log.logger import mLogInfo, mLogError

class Fun(commands.Cog, name='fun'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
        self.__handler = fun.FunHandler()
        mLogInfo('Fun cog initialized')

    @commands.Cog.listener()
    async def on_ready(self):
        mLogInfo('Fun cog is ready')

    
