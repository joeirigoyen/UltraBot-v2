# Specific imports
from discord import app_commands
from discord import  FFmpegPCMAudio, Guild, Interaction
from discord.ext import commands

# Custom imports
from entities.workers.music.music import Player, Song
from log.logger import mLogInfo, mLogError

class Music(commands.Cog, name='music'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
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
    @app_commands.describe(url='The URL of the song to play')
    @app_commands.describe(force_next='(optional) Force the song to play next.')
    async def mPlay(self, aCtx: Interaction, url: str, force_next: bool = False):
        mLogInfo(f'Play command received with url: {url}')
        # Get song data
        _song = Song(url)
        # Spawn player and intialize a playlist
        _player = Player()
        _playlist = _player.mGetPlaylist(self.mGetGuild(aCtx))
        # Add the song to the playlist
        if force_next:
            _playlist.mForceNext(_song)
        else:
            _playlist.mQueueSong(_song)
        # Play the song
        await _player.mPlay(aCtx, _song)
