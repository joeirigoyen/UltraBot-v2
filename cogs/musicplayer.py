# Specific imports
from discord import app_commands
from discord import  FFmpegPCMAudio, Guild, Interaction
from discord.ext import commands

# Custom imports
from entities.utils.rare import mSuperCleanString
from entities.utils.musicutils import MusicDownloader
from entities.workers.music.music import Player
from log.logger import mLogInfo, mLogError

class Music(commands.Cog, name='music'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
        self.__downloader = MusicDownloader()
        self.__player = Player()
        mLogInfo('Music cog initialized')

    def mGetGuild(self, aCtx: Interaction) -> Guild:
        for _guild in self.__bot.guilds:
            if aCtx.guild.id == _guild.id:
                return _guild
        return aCtx.user.guild

    @commands.Cog.listener()
    async def on_ready(self):
        mLogInfo('Music cog is ready')

    @app_commands.command(name='play', description='Play a song')
    @app_commands.describe(urls='The URLs of the song to play')
    async def mPlay(self, aCtx: Interaction, urls: str):
        # Split each url separated by commas
        _urls = [_url.strip() for _url in urls.split(',')]
        mLogInfo(f'Play command received with urls: {_urls}')
        # Download songs and get the list of download paths
        await aCtx.response.defer(thinking=True)
        _songs = await self.__downloader.mDownloadQueue(_urls)
        mLogInfo(f'Downloaded songs: {_songs}')
        # Add songs to playlist
        _author = mSuperCleanString(aCtx.user.name)
        _songsMetadata = [{"author": _author, "path": _path} for _path in _songs]
        mLogInfo(f'Adding songs to queue: {_songsMetadata}')
        self.__player.mAddSongsToQueue(self.mGetGuild(aCtx), _songsMetadata)
        # Start playing
        await self.__player.mPlay(aCtx)
        await aCtx.followup.send(f'Downloaded songs: {", ".join(_songs)}', ephemeral=True)

    @app_commands.command(name='musicping', description='Ping the bot')
    async def mPing(self, aCtx: Interaction):
        mLogInfo('Ping command received')
        await aCtx.response.send_message('Pong!', ephemeral=True)
