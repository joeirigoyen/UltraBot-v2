# General imports
import io
import os
import random

# Specific imports
from discord import Color, Embed, FFmpegPCMAudio, Guild, Interaction, VoiceChannel, VoiceClient
from typing import Optional


# Custom imports
from log.logger import mLogInfo, mLogError

class Song:
    def __init__(self, aPath: str, aAuthor: str) -> None:
        # Song data
        mLogInfo(f"Creating song object for {aPath} by {aAuthor}")
        self.__path: str = aPath
        self.__title: str = f"{os.path.basename(self.__path)} by {aAuthor}"
        # Song queue
        self.__next: Song = None
        self.__previous: Song = None

    @property
    def title(self) -> str:
        return self.__title
    
    @property
    def path(self) -> str:
        return self.__path
    
    @property
    def next(self) -> Optional['Song']:
        return self.__next
    
    @property
    def previous(self) -> Optional['Song']:
        return self.__previous

    @next.setter
    def next(self, aNext: Optional['Song']) -> None:
        # Skip if setting an empty song as next
        mLogInfo(f"Setting next song: {aNext.title if aNext else 'None'}")
        if not aNext:
            return
        self.next = aNext

    @previous.setter
    def previous(self, aPrevious: Optional['Song']) -> None:
        # Skip if setting an empty song as previous
        mLogInfo(f"Setting previous song: {aPrevious.title if aPrevious else 'None'}")
        if not aPrevious:
            mLogInfo("No previous song to set. Skipping.")
            return
        self.previous = aPrevious

    def mCanPlay(self, aCtx: Interaction) -> bool:
        # Check if author is in a voice channel or if the user is deafened
        if not aCtx.user.voice or aCtx.user.voice.deaf:
            return False
        return True

    def mPlay(self, aCtx: Interaction, aVoiceClient: VoiceClient, aCallback) -> None:
        if not self.__path:
            mLogError("Cannot play song without a valid path.")
            return
        # Create an FFmpegPCMAudio source
        if self.mCanPlay(aCtx):
            mLogInfo(f"Playing song: {self.__title} in {aVoiceClient.channel.name}")
            _pcm_audio = FFmpegPCMAudio(self.__path)
            # Pass the callback into the after argument without executing it
            aVoiceClient.play(_pcm_audio, after=lambda error: aCallback(error, aCtx) if aCallback else None)

    def mStop(self, aVoiceClient: VoiceClient) -> None:
        if aVoiceClient.is_playing():
            mLogInfo(f"Stopping song: {self.__title}")
            aVoiceClient.stop()
        else:
            mLogError(f"Cannot stop song as nothing is currently playing.")

class Playlist:
    def __init__(self) -> None:
        self.__queue = []
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

    @property
    def current(self) -> Song:
        return self.__current

    @current.setter
    def current(self, aSong: Song) -> None:
        if not aSong:
            mLogError("Cannot set current song to None.")
            return
        self.__current = aSong
        # If the song is already in the queue, remove it unless looping is enabled
        if aSong in self.__queue and not self.__loop:
            self.__queue.remove(aSong)

    def mPlayNext(self) -> None:
        if not self.__current:
            mLogError("No current song to play next.")
            return
        # If shuffle is enabled, pick a random song from the queue
        if self.__shuffle and len(self.__queue) > 1:
            _nextSong = random.choice(self.__queue)
        else:
            _nextSong = self.__current.next
        # If no next song, loop back to the start if looping is enabled
        if not _nextSong and self.__loop:
            _nextSong = self.__queue[0] if self.__queue else None
        # Set the current song to the next song
        self.current = _nextSong

    def mQueueSongs(self, aSongList: list[dict]) -> None:
        _previous = self.__queue[-1] if len(self.__queue) >= 1 else None
        mLogInfo(f"Previous song: {_previous.title if _previous else 'None'}")
        for _song in aSongList:
            # Retrieve metadata from song list
            _author, _path = _song.get('author', 'Unknown'), _song.get('path')
            mLogInfo(f"Adding song: {_path} by {_author}")
            if not _path:
                mLogError("No path in one of the songs. Cannot add to queue.")
            # Create song object and set previous/next song (if any)
            _songObj = Song(_path, _author)
            if _songObj:
                mLogInfo(f"Created song object: {_songObj.title}")
            else:
                mLogError(f"Failed to create song object for {_path}. Skipping.")
                continue
            _songObj.previous = _previous
            # Sometimes previous song is None, so we need to check
            if _songObj.previous:
                _songObj.previous.next = _songObj
            if not _previous:
                self.__current = _songObj
            _previous = _songObj
            mLogInfo(f"Added song: {_songObj.title} to the queue.")
        mLogInfo(f"Added {len(aSongList)} songs to the queue.")
        mLogInfo(f"Current song: {self.__current.title if self.__current else 'None'}")

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

    async def mRegisterVC(self, aCtx: Interaction) -> None:
        self.__voiceChannel = aCtx.user.voice.channel
        # Check if the bot is already connected to a voice channel in this guild
        _voiceClient = aCtx.guild.voice_client
        if _voiceClient:
            if _voiceClient.is_connected():
                if _voiceClient.channel != self.__voiceChannel:
                    await _voiceClient.move_to(self.__voiceChannel)
                self.__voiceClient = _voiceClient
                return
            else:
                # Ghost connection state, force disconnect
                mLogError("Found disconnected voice client. Cleaning up before reconnect...")
                await _voiceClient.disconnect(force=True)

        # Attempt to connect natively
        try:
            mLogInfo(f"Attempting to connect to voice channel: {self.__voiceChannel.name}")
            self.__voiceClient = await self.__voiceChannel.connect(timeout=20.0, reconnect=True)
        except Exception as e:
            mLogError(f"Voice connection failed: {e}. Returning early.")
            self.__voiceClient = None

    def mAddSongsToQueue(self, aGuild: Guild, aMetadata: list[dict]) -> None:
        _playlist = self.mGetPlaylist(aGuild)
        _playlist.mQueueSongs(aMetadata)

    def mGetPlaylist(self, aGuild: Guild) -> Playlist:
        if not self.__playlists.get(aGuild.id):
            self.__playlists[aGuild.id] = Playlist()
        return self.__playlists[aGuild.id]

    async def mPlay(self, aCtx: Interaction) -> None:
        # Register voice client
        if not aCtx.user.voice:
            mLogInfo(f'User {aCtx.user.name} is not in a voice channel.')
            return
        await self.mRegisterVC(aCtx)
        if not self.__voiceClient:
            mLogError("Aborting playback: Voice connection could not be established.")
            await aCtx.followup.send("Failed to connect to the voice channel. Please try again later.", ephemeral=True)
            return

        # Check if the player is already playing something
        if self.__voiceClient.is_playing():
            mLogInfo("Bot is already playing. New songs appended to queue.")
            return
            
        # Play the current song
        _playlist = self.mGetPlaylist(self.__voiceChannel.guild)
        _current: Song = _playlist.current
        if not _current:
            mLogError("No song to play. Please add songs to the queue.")
            return
        _current.mPlay(aCtx, self.__voiceClient, self.mSongFinishedCallback)

    def mSongFinishedCallback(self, error: Exception, aCtx: Interaction) -> None:
        if error:
            mLogError(f"Player error: {error}")
            
        _playlist = self.mGetPlaylist(aCtx.guild)
        _playlist.mPlayNext()
        
        _next: Song = _playlist.current
        if _next:
            mLogInfo(f"Queue advancing to: {_next.title}")
            _next.mPlay(aCtx, self.__voiceClient, self.mSongFinishedCallback)
        else:
            mLogInfo("Queue finished.")
