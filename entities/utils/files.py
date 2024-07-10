# Generic imports
import csv
import gdown
import json
import os
import re
import time
import zipfile

# Specific imports
from urllib.request import urlretrieve

# Custom imports
from entities.utils.rare import mGenerateProjectId, mIsProjectId, mCleanString
from log.logger import mLogError, mLogInfo

def mGetCurDir() -> str:
    return os.path.dirname(os.path.realpath(__file__))

def mGetAssetsDir() -> str:
    _curDir = mGetCurDir()
    _parentDir = mGetParent(_curDir, 2)
    return os.path.join(_parentDir, 'assets')

def mGetConfigDir() -> str:
    _curDir = mGetCurDir()
    _parentDir = mGetParent(_curDir, 2)
    return os.path.join(_parentDir, 'config')

def mGetParent(aPath: str, aDepth: int = 1) -> str:
    _path = aPath
    for _ in range(aDepth):
        _path = os.path.dirname(_path)
    return _path

def mGetBaseDir() -> str:
    _curDir = mGetCurDir()
    _parentDir = mGetParent(_curDir, 2)
    return _parentDir

def mEnsureFile(aFilePath: str, aCopy: str = None) -> str:
    # Check if file exists
    if not os.path.exists(aFilePath):
        # Create file
        with open(aFilePath, 'w') as _file:
            if aCopy:
                with open(aCopy, 'r') as _copy:
                    _file.write(_copy.read())
                    mLogInfo(f'File {aFilePath} created from {aCopy}')
            mLogInfo(f'File {aFilePath} created since it did not exist.')
    return aFilePath

def mOpenFile(aPath: str) -> object:
    # Check if file exists
    if not os.path.exists(aPath):
        raise FileNotFoundError(f'File {aPath} does not exist')

    # Open file
    _file = open(aPath, 'r')
    mLogInfo(f'File {aPath} opened')
    return _file

def mParseJsonFile(aPath: str) -> dict:
    # Open file
    _file = mOpenFile(aPath)

    # Try to parse JSON data
    _data = _file.read()
    try:
        _jsonData = json.loads(_data)
    except json.JSONDecodeError:
        mLogError(f'File {aPath} is not a valid JSON file. Returning empty dictionary')
        _file.close()
        return {}

    # Close file
    _file.close()
    return _jsonData

def mWriteJsonFile(aPath: str, aData: dict) -> None:
    # Open file
    _file = open(aPath, 'w')
    mLogInfo(f'File {aPath} opened')

    # Write JSON data
    _file.write(json.dumps(aData, indent=4))
    
    # Close file
    _file.close()
    mLogInfo(f'File {aPath} written')

def mAddImgPlaceholders(aPath: str) -> None:
    # Open file
    _data = mParseJsonFile(aPath)
    
    # Transform JSON data
    for _perkId in _data:
        # Get all the information of the perk
        _perk: dict = _data[_perkId]
        
        # Add img placeholder
        _cleanTitle = mCleanString(_perk['title'])
        _imgPath = f'assets/dbd/imgs/perks/{_cleanTitle}.png'
        _perk['img'] = _imgPath
        
        # Set new img path in JSON data
        _data[_perkId] = _perk
        
    # Write dict to file
    with open(aPath, 'w') as _file:
        json.dump(_data, _file, indent=4)

def mCleanPerkImgFiles() -> None:
    # Make set of img paths under the given directory
    _imgDir = mGetDBDConfig()['PERKS_IMG_DIR']
    _imgPath = mGetFile(_imgDir)

    for _root, _, _files in os.walk(_imgPath):
        for _file in _files:
            # Skip if file is a project id already
            mLogInfo(f'Processing file {_file}')
            _basename = os.path.splitext(os.path.basename(_file))[0]
            if mIsProjectId(_basename):
                mLogInfo("File is already valid.")
                continue
            # Get clean name of the file
            _cleanName = mCleanString(_basename)
            _newPath = os.path.join(_root, f'{_cleanName}.png')
            # Move image to new path
            mRenameFile(os.path.join(_root, _file), _newPath)

def mRenameFile(aPath: str, aNewPath: str) -> None:
    # Check if file exists
    if not os.path.exists(aPath):
        raise FileNotFoundError(f'File {aPath} does not exist')

    # Rename file
    os.rename(aPath, aNewPath)
    mLogInfo(f'File {aPath} renamed to {aNewPath}')

def mUpdatePerksImgPaths(aPath: str) -> None:
    # Open file
    _data = mParseJsonFile(aPath)
    
    # Transform JSON data
    for _perkId in _data:
        # Get all the information of the perk
        _perk: dict = _data[_perkId]
        
        # Make new image path 
        _config = mGetDBDConfig()
        _imgPath = _config['PERKS_IMG_DIR']
        _imgDir = mGetFile(_imgPath)
        _newImgPath = os.path.join(_imgDir, f'{_perkId}.png')
        
        # Move image to new path
        mRenameFile(_perk['img'], _newImgPath)
        
        # Set new img path in JSON data
        _perk['img'] = _newImgPath
        _data[_perkId] = _perk
        
    # Write dict to file
    with open(aPath, 'w') as _file:
        json.dump(_data, _file, indent=4)

# Delete files that are not project ids
def mCleanNonProjectIds(aPath: str) -> None:
    # Walk through directory
    for _root, _, _files in os.walk(aPath):
        for _file in _files:
            # Check if file is a project id
            if mIsProjectId(_file):
                continue
            # Delete file
            _filePath = os.path.join(_root, _file)
            # os.remove(_filePath)
            mLogInfo(f'File {_filePath} deleted')

def mUpdatePerksJSON(aPath: str) -> None:
    # Open file
    _data = mParseJsonFile(aPath)
    _newData = {}

    # Transform JSON data
    for _perkId in _data:
        mLogInfo(f'Processing perk {_perkId}')
        
        # Get a copy of the information of the perk
        _perk: dict = _data[_perkId]
        
        # Check if uuid complies with the project format
        _imgBaseName = os.path.basename(_perk['img'])
        _imgNoExt = os.path.splitext(_imgBaseName)[0]
        _uuid = _perkId

        if not mIsProjectId(_uuid):
            # Create new perk with new title
            mLogInfo(f'Perk {_perkId} does not have a valid UUID')
            _uuid = mGenerateProjectId()
            mLogInfo(f'New UUID for perk {_perkId}: {_uuid}')
            _newData[_uuid] = _perk
            mLogInfo(f'Perk now is: {_newData[_uuid]}')
        
        # Check if img path matches the UUID
        if _imgNoExt != _uuid:
            # Create new img path
            _newImgPath = os.path.join(os.path.dirname(_perk['img']), f'{_uuid}.png')
            mLogInfo(f'New img path for perk {_uuid}: {_newImgPath}')
            # Move image to new path
            mRenameFile(_perk['img'], _newImgPath)
            # Update img path in perk data
            _perk['img'] = _newImgPath
    
    # Write dict to file
    with open(aPath, 'w') as _file:
        json.dump(_newData, _file, indent=4)

def mMakeUserFile(aUserId: str, aPath: str) -> str:
    # Skip if user_id is empty
    if not aUserId:
        return aPath
    # Extract directory and original filename from aPath
    _dir = os.path.dirname(aPath)
    _originalFilename = os.path.basename(aPath)
    # Alter filename to include user_id
    _filename, _ext = os.path.splitext(_originalFilename)
    _filename = f"{aUserId}_{_filename}"
    _ext = _ext.lstrip('.')  # Remove the dot from the extension
    mLogInfo(f"Original filename: {_originalFilename}")

    # Regex pattern to match filenames and extract repeated_count
    _pattern = re.compile(rf"{re.escape(str(_filename))}")
    mLogInfo(f"Scanning for pattern: {_pattern.pattern} in directory {_dir}")

    # Get the list of files in the directory
    _currentFiles = os.listdir(_dir)
    mLogInfo(f"Found {_currentFiles} files in the directory")

    # Find the highest repeated_count for the given user_id and filename
    _count = 0
    for file in _currentFiles:
        match = _pattern.match(file)
        if match:
            _count += 1
    mLogInfo(f"Found {_count} files with the pattern")

    # Increment the repeated_count for the new file
    new_count = _count + 1

    # Construct the new filename
    new_filename = f"{_filename}_{new_count}.{_ext}"
    
    # Create the new file path
    new_file_path = os.path.join(_dir, new_filename)
    
    # Rename the original file to the new file path
    mLogInfo(f"Renamed file to: {new_file_path}")
    return new_file_path

def mGetFile(aRelativePath: str, aCheck: bool = False) -> str:
    # Get base directory
    _baseDir = mGetBaseDir()
    _fullPath = os.path.join(_baseDir, aRelativePath)

    # Check if file exists
    if not os.path.exists(aRelativePath) and aCheck:
        raise FileNotFoundError(f'File {aRelativePath} does not exist')

    # Return file
    return _fullPath

def mCleanupDir(aDir: str, aMinutes: int) -> None:
    # Get all files in the directory older than a certain amount of hours
    _files = os.listdir(aDir)
    _now = time.time()
    _before = _now - aMinutes * 60
    _filesToDelete = [os.path.join(aDir, _file) for _file in _files if os.path.getmtime(os.path.join(aDir, _file)) < _before]
    # Delete all files in list
    for _file in _filesToDelete:
        os.remove(_file)
        mLogInfo(f'File {_file} deleted')

def mGetDBDConfig() -> dict:
    # Get config file
    _configFile = mGetFile('config/dbdconfig.json')
    _config = mParseJsonFile(_configFile)
    return _config

def mCleanupDbdGenImgsDir() -> None:
    # Get config
    _config = mGetDBDConfig()
    # Get dbd generated images directory
    try:
        _imgsDir = mGetFile(_config['GENERATED_IMG_DIR'], aCheck=True)
    except FileNotFoundError:
        mLogError('DBD generated images directory not found')
        return
    # Get cleanup interval
    _maxImgAge = _config['MAX_GENERATED_IMG_AGE']
    # Cleanup directory
    mCleanupDir(_imgsDir, _maxImgAge)

def mGetDBDDataDir() -> str:
    # Get config
    _assetsDir = mGetAssetsDir()
    _dbdAssetsDir = os.path.join(_assetsDir, 'dbd')
    _dbdDataDir = os.path.join(_dbdAssetsDir, 'data')
    return _dbdDataDir

def mExtractCSVData(aPath: str) -> list[dict]:
    with open(aPath, 'r') as _file:
        # Read CSV data
        _csvReader = csv.DictReader(_file)
        # Extract data
        _data = [row for row in _csvReader]
        return _data

def mExtractCSVColumn(aPath: str, aColumn: str) -> list[str]:
    # Extract data
    with open(aPath, 'r') as _file:
        # Read CSV data
        _csvReader = csv.DictReader(_file)
        # Extract data
        _data = [row[aColumn] for row in _csvReader]
        return _data

# Get a map of the id and the name of the perk from a JSON file
def mGetIdTitleMap(aPath: str) -> dict:
    # Open file
    _data = mParseJsonFile(aPath)
    _map = {}
    # Extract data
    for _perkId in _data:
        _perk = _data[_perkId]
        _map[_perkId] = _perk['title']
    return _map

# Get a map of the id and the name of the perk from a CSV file
def mGetIdTitleMapCSV(aPath: str) -> dict:
    # Extract data
    _data = mExtractCSVData(aPath)
    _map = {}
    # Extract data
    for _perk in _data:
        _map[_perk['id']] = _perk['title']
    return _map

# Find differences between two maps sets of keys
def mFindDifferentTitles(aMap1: dict, aMap2: dict) -> list:
    # Check if keys are the same
    _keys1 = set(aMap1.keys())
    _keys2 = set(aMap2.keys())
    
    _diffValues = []
    _diffs = _keys1.symmetric_difference(_keys2) 
    if len(_diffs) == 0:
        mLogInfo('Maps have the same keys')
        return _diffValues
    
    # Return differences
    for _diff in _diffs:
        if _diff in _keys1:
            _diffValues.append(aMap1[_diff])
        elif _diff in _keys2:
            _diffValues.append(aMap2[_diff])

    return _diffValues

# Find differences between two files and update the second file
def mUpdateCSVBasedOnJSONFile(aJsonPath: str, aCsvPath: str) -> None:
    # Get maps from files
    _jsonMap = mGetIdTitleMap(aJsonPath)
    _csvMap = mGetIdTitleMapCSV(aCsvPath)
    # Find differences
    _diffs = mFindDifferentTitles(_jsonMap, _csvMap)
    # Update CSV file
    if not len(_diffs) > 0:
        mLogInfo('No differences found between JSON and CSV files')
        return
    
    mLogInfo(f'{len(_diffs)} differences found between JSON and CSV files')
    mLogInfo('Updating CSV file')
    # Open CSV file
    with open(aCsvPath, 'w') as _file:
        # Write CSV data
        _csvWriter = csv.DictWriter(_file, fieldnames=['id', 'title'])
        _csvWriter.writeheader()
        for _perkId in _jsonMap:
            _perk = _jsonMap[_perkId]
            _csvWriter.writerow({'id': _perkId, 'title': _perk})
    mLogInfo('CSV file updated')

# Download files from an URL from Google Drive
def mDownloadFromGDrive(aUrl: str, aPath: str) -> None:
    # Get file id from URL
    _match = re.search(r'(?<=d\/)(.*?)(?=\/view\?)', aUrl)
    if not _match:
        mLogError(f'URL {aUrl} is not valid')
        return
    _fileId = _match.group(0)
    # Get file
    gdown.download(f'https://drive.google.com/uc?id={_fileId}', aPath, quiet=True)

# Extract a zip file
def mExtractZip(aZipPath: str, aExtractPath: str, aRemoveWhenDone: bool = False) -> None:
    with zipfile.ZipFile(aZipPath, 'r') as _zip:
        _zip.extractall(aExtractPath)
    # Remove zip file
    if aRemoveWhenDone:
        os.remove(aZipPath)
