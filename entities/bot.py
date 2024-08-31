# Specific imports
from dotenv import load_dotenv
from discord import Intents, Activity, ActivityType, Object
from discord.ext import commands
from os import getenv

# Custom imports
from cogs.dbd import Dbd
from cogs.musicplayer import Music
from log.logger import mLogInfo, mLogError, mGetHandler

# Add intents to the bot
def mLoadIntents():
    """
    Initialize the intents of the bot.
    """
    intents = Intents.default()
    mLogInfo('Default intents set')

    # Additions to the default intents
    intents.members = True
    intents.message_content = True
    intents.dm_messages = True
    intents.guild_messages = True
    intents.guilds = True
    intents.reactions = True
    intents.presences = True
    intents.voice_states = True
    mLogInfo('Additional intents set')

    return intents

# Global bot instance
bot = commands.Bot(command_prefix='$', intents=mLoadIntents())

# Add a cog to the bot
async def mAddCog(aCog: commands.Cog):
    """
    Add a cog to the bot.

    Args:
        aCog (commands.Cog): The cog to add.
    """
    try:
        await bot.add_cog(aCog)
        mLogInfo(f'Added {aCog}')
    except Exception as e:
        mLogError(f'Could not add {aCog}: {e}')

@bot.event
async def on_ready():
    """
    Called when the bot is ready.
    """
    # Log the bot's name
    mLogInfo(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=Activity(type=ActivityType.playing, name='$help'))

async def mSetup():
    """
    Set up the bot with the given token.
    """
    # Load the environment variables
    load_dotenv()
    _guildId = getenv('DISCORD_GUILD')
    _guildObj = Object(id=_guildId)
    # Add cogs to the bot
    mLogInfo('Adding cogs')
    await mAddCog(Dbd(bot))
    await mAddCog(Music(bot))
    mLogInfo(f'Current cogs: {bot.cogs}')
    # Sync commands
    bot.tree.copy_global_to(guild=_guildObj)
    await bot.tree.sync(guild=_guildObj)

def mRun(aToken: str):
    """
    Run the bot with the given token and log handler.

    Args:
        aToken (str): The token of the bot.
    """
    # Run the bot
    mLogInfo('Running bot')
    bot.setup_hook = mSetup
    bot.run(aToken, log_handler=mGetHandler('trace'))
