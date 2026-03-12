import asyncio
import os
import shlex
import subprocess
import yt_dlp

from multiprocessing import Pool

from log.logger import mLogError, mLogInfo, mLogDebug


class MusicDownloader:
    def __init__(self):
        # File paths
        self.__entitiesDir = os.path.dirname(os.path.abspath(__file__))
        self.__saveDir = os.path.join(self.__entitiesDir, "musicdownloads")
        self.__exeFilePath = os.path.join(self.__entitiesDir, "yt-dlp.exe")
        # URL queue
        self.__queue = []

    def mCountSongsInFolder(self) -> int:
        return sum(len(_files) for _, _, _files in os.walk(self.__saveDir))

    def mGenerateSongTitle(self) -> str:
        _currSongs = self.mCountSongsInFolder()
        return f"downloaded_{_currSongs:05d}"

    def mDownloadSong(self, aUrl: str) -> str | None:
        # Generate the song title to create the full download path
        _title = self.mGenerateSongTitle()
        _savePath = os.path.join(self.__saveDir, _title)
        # Execute download command using yt-dlp
        mLogInfo(f"Downloading {aUrl} at {_savePath}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': _savePath,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }],
            'quiet': True,
            'noplaylist': True,
        }
        # Check for errors and notify in case any was returned as part of stderr
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([aUrl])
            mLogInfo(f"Successfully downloaded {aUrl} as {_savePath}")
            return f"{_savePath}.mp3"
        except Exception as e:
            mLogError(f"Error during download of {aUrl}: {e}")
            return None

    async def mDownloadQueue(self, aUrlList: list[str]) -> list[str]:
        # Return the list of download paths after finishing the bulk download
        self.__queue = aUrlList
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, self.mDownloadSong, url)
            for url in self.__queue
        ]
        _results = await asyncio.gather(*tasks)
        if not all(_results):
            _errCount = len([_false for _false in _results if not _false])
            mLogInfo(f"{_errCount} downloads completed with errors.")
        mLogInfo("All downloads were completed successfully.")
        return _results
