# General imports
import os

# Specific imports
from PIL import Image, ImageDraw, ImageFont

# Custom imports
from log.logger import mLogInfo
from entities.utils.files import mMakeUserFile

def mCreateCollage(aImagePaths: list[str], aWidth: int, aHeight: int, aTitle=None, aOffset: int = 5) -> Image:
    # Initialize the width and height of the image
    _titleOffset = 15 if aTitle else 0
    _totalWidth = aWidth + (aOffset * (len(aImagePaths) - 1))
    _totalHeight = aHeight + _titleOffset

    # Create a new image with the given width and height
    _collage = Image.new('RGBA', (_totalWidth, _totalHeight))

    # Initialize the positions
    _x ,_y = 0, _titleOffset

    # Initialize width per image
    _w, _h = aWidth // len(aImagePaths), aWidth // len(aImagePaths)

    # Add the title in the top center of the image
    if aTitle:
        _draw = ImageDraw.Draw(_collage)
        _font = ImageFont.load_default(18)
        _draw.text((_x + _totalWidth // 2, 0), aTitle, fill='white', font=_font, anchor='mt', align='center')

    # Paste the images into the collage
    for _img in aImagePaths:
        # Resize the image
        _perkImg = Image.open(_img).resize((_w, _h))
        # Add the image
        _collage.paste(_perkImg, (_x, _y))
        # Update the position
        _x += _w + aOffset

    # Return the collage
    mLogInfo(f'Collage of size {_totalWidth}x{_totalHeight} created with title {aTitle if aTitle else "None"}')
    return _collage

def mSaveImage(aImage: Image, aPath: str, aUserId: str) -> str:
    # Make user path
    _path = mMakeUserFile(aUserId, aPath)
    # Save the image
    aImage.save(_path)
    mLogInfo(f'Image saved to {_path}')
    return _path

