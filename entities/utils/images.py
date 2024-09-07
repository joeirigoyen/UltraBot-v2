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

def mSaveImage(aImage: Image, aPath: str) -> str:
    # Check if the filename already exists
    _counter = 0
    _parentDir = os.path.dirname(aPath)
    _basename = os.path.basename(aPath)
    _filename = os.path.splitext(_basename)[0]
    _extension = os.path.splitext(_basename)[1]
    
    for _file in os.listdir(_parentDir):
        if _file.startswith(_filename):
            _counter += 1
    
    # Create the new filename
    _path = os.path.join(_parentDir, f'{_filename}_{_counter:03}.{_extension}')
    
    # Save the image
    aImage.save(_path)
    mLogInfo(f'Image saved to {_path}')
    return _path

