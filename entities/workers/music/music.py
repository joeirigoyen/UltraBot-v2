# General imports
import random

# Specific imports
from discord import Color, Embed, Guild, Interaction, VoiceChannel
from typing import Optional


# Custom imports
from entities.utils.musicutils import mGetSource
from log.logger import mLogInfo, mLogError

class Song:
    def __init__(self, aUrl: str) -> None:
        # Song data
        self.__url: str = aUrl
        self.__title: str = None
        self.__duration: int = None
        self.__output = None
        # Song queue
        self.__next: Song = None
        self.__previous: Song = None

    @property
    def title(self) -> str:
        return self.__title
    
    @property
    def url(self) -> str:
        return self.__url
    
    @property
    def duration(self) -> int:
        return self.__duration
    
    @property
    def output(self) -> str:
        return self.__output
    
    @property
    def next(self) -> Optional['Song']:
        return self.__next
    
    @property
    def previous(self) -> Optional['Song']:
        return self.__previous
    
    def mGetOutput(self) -> str:
        """Create an embed with the song information

        Returns:
            Embed: The embed with the song information
        """
        _embed = Embed(title=self.title, color=Color.random())
        if self.duration:
            _embed.add_field(name='Duration:', value=self.duration)
        if self.url:
            _embed.add_field(name='URL:', value=self.url)
        if self.next:
            _embed.add_field(name='Up next:', value=self.next.title)
        if self.previous:
            _embed.add_field(name='Previously:', value=self.previous.title)
        return _embed

    def mGetSource(self) -> None:
        # Get info sources
        _info, _path = mGetSource(self.url)
        _formats: list[dict] = _info.get('formats', [{}])
        _source = _formats[0].get('url', None)
        # Set song data
        self.__title = _info.get('title', 'Unknown Song')
        self.__duration = _info.get('duration', 0)
        self.__output = _path
        


class Playlist:
    def __init__(self) -> None:
        self.__current: Song = None
        self.__loop: bool = False
        self.__shuffle: bool = False

    def __len__(self) -> int:
        _count = 0
        _current = self.__current
        while _current:
            _count += 1
            _current = _current.next
        return _count

    def __iter__(self):
        _current = self.__current
        while _current:
            yield _current
            _current = _current.next

    def mQueueSong(self, aSong: Song) -> None:
        # Set song to current if no song is playing
        if not self.__current:
            self.__current = aSong
            return
        # Add song to the end of the playlist
        _current = self.__current
        while _current.next:
            _current = _current.next
        _current.next = aSong
        aSong.previous = _current

    def mForceNext(self, aSong: Song) -> None:
        # Set song to current if no song is playing
        if not self.__current:
            self.__current = aSong
            return
        # If no next song, add this song to the front
        aSong.previous = self.__current
        if not self.__current.next:
            self.__current.next = aSong
            return
        aSong.next = self.__current.next

    def mEmpty(self) -> None:
        self.__current = None


class Player:
    def __init__(self) -> None:
        self.__playlists: dict[int, Playlist] = {}

    async def mRegisterVC(self, aVoiceChannel: VoiceChannel) -> None:
        self.__voiceChannel = aVoiceChannel
        self.__voiceClient = await self.__voiceChannel.connect()

    def mGetPlaylist(self, aGuild: Guild) -> Playlist:
        if not self.__playlists.get(aGuild.id):
            self.__playlists[aGuild.id] = Playlist()
        return self.__playlists[aGuild.id]

    async def mCanPlay(self, aCtx: Interaction) -> bool:
        # Check if author is in a voice channel
        if not aCtx.user.voice:
            await aCtx.response.send_message('You need to be in a voice channel to play music.', ephemeral=True)
            return False
        # Check if user is not deafened
        if aCtx.user.voice.deaf:
            await aCtx.response.send_message('You cannot play music while deafened.', ephemeral=True)
            return False
        return True

    async def mPlay(self, aCtx: Interaction, aSong: Song, aForceNext: bool = False) -> None:
        # Register voice client
        if not aCtx.user.voice:
            mLogInfo(f'User {aCtx.user.name} is not in a voice channel.')
            return
        await self.mRegisterVC(aCtx.user.voice.channel)
        # Queue song
        _playlist = self.mGetPlaylist()
        if aForceNext:
            _playlist.mForceNext(aSong)
        else:
            _playlist.mQueueSong(aSong)
        await self.__voiceClient.play(aSong.output)

    def mAfterPlay(self, aCtx: Interaction):
        self.__playlist.__current = self.__playlist.__current.next
        if self.__playlist.__current:
            next_song = self.__playlist.__current
            self.mPlay(aCtx, next_song)
        else:
            mLogInfo('Playlist is empty.')