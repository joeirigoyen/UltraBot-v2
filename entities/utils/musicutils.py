import os
from typing import Tuple, Any

import youtube_dl as ydl

from entities.utils.files import mGetMusicConfig

async def mGetSource(aUrl: str) -> tuple[Any, str]:
    """
    Get the source of a URL.

    Args:
        aUrl (str): The URL to get the source of.

    Returns:
        ydl.YoutubeDL: The source of the URL.
    """
    _ydlOptions = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }

    with ydl.YoutubeDL(_ydlOptions) as _ydl:
        # Extract song info
        _info = _ydl.extract_info(aUrl, download=False)
        _songName: str = _info.get('title', 'Unknown Song')
        # Remove special characters from the song name
        _songName = ''.join(e for e in _songName if e.isalnum())[:20]
        # Set the download directory
        _downloadDir = mGetMusicConfig().get('DOWNLOAD_PATH')
        _fileName = os.path.join(_downloadDir, f'{_songName}.{_ydlOptions.get("audioformat")}')
        _ydl.prepare_filename(_fileName)
        _ydl.download([aUrl])

    return _info, _fileName
