# Generic imports
import os

# Specific imports
from discord import File, Interaction

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.datahandler import DBDDataHandler
from entities.utils.files import mGetAssetsDir, mGetDBDDataDir, mGetFile, mEnsureFile
from entities.utils.images import mCreateCollage, mSaveImage
from entities.workers.dbd.perks import PerkTracker


class DbdWorker:

    __assetsDir = mGetAssetsDir()
    __dbdAssetsDir = os.path.join(__assetsDir, 'dbd')
    __dbdGenImagesDir = os.path.join(__dbdAssetsDir, 'imgs', 'generated')
    __dbdPerkUsagePath = os.path.join(mGetDBDDataDir(), 'dbdperkusage.csv')

    def __init__(self, aCtx: Interaction):
        super().__init__()
        # Set owner
        self.__userId = str(aCtx.user.id)
        self.__userName = aCtx.user.name
        # Get blacklist from config
        self.__tracker = PerkTracker(self.__userId, self.__userName)
        self.__running = False
        # Load data handler
        self.__dbdUserPerkUsagePath = os.path.join(mGetDBDDataDir(), 'generated', f'{self.__userId}_dbdperkusage.csv')
        self.__dataHandler = DBDDataHandler(self.__dbdPerkUsagePath)
        self.__userDataHandler = DBDDataHandler(self.__dbdUserPerkUsagePath)
        # Log worker creation
        mLogInfo(f'Worker {self.__userId} created')

    @property
    def userId(self):
        return self.__userId
    
    @property
    def userName(self):
        return self.__userName

    def mIsRunning(self):
        return self.__running

    def mStart(self):
        if not self.mIsRunning():
            self.__running = True
            mLogInfo(f'Worker {self.__userId} started')
        else:
            mLogError(f'Worker {self.__userId} is already running')

    def mStop(self):
        if self.mIsRunning():
            self.__running = False
            mLogInfo(f'Worker {self.__userId} stopped')
        else:
            mLogError(f'Worker {self.__userId} is not running')

    def mGetUserBlackList(self) -> set:
        return self.__tracker.mGetBlackList()

    def mSetLastMessage(self, aMessageId: str) -> None:
        self.__tracker.mSetLastMessage(aMessageId)

    def mGetLastMessage(self) -> str:
        return self.__tracker.mGetLastMessage()

    def mSetLastBuildId(self, aBuildId: int) -> None:
        self.__tracker.mSetLastBuildId(aBuildId)

    def mGetLastBuildId(self) -> int:
        return self.__tracker.mGetLastBuildId()

    def mGenerateCollage(self, aCtx: Interaction, aBuild: list) -> File:
        # For each perk in aBuild, get the image
        _images = self.__tracker.mGetImages(aBuild)
        # Get username
        _username = aCtx.user.name
        # Get title
        _title = f'Build for user {_username}'
        # Create and save collage
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath, self.__userId)
        return File(_imagePath)

    def mGetRandomBuild(self, aCtx: Interaction):
        # Log start of method
        mLogInfo(f'Random build requested for user {self.__userId}')
        
        # Get four random perks
        _build = self.__tracker.mGetRoll()
        _buildNames = [self.__tracker.mGetPerkName(_id) for _id in _build]
        _images = self.__tracker.mGetImages(_build)
        
        # Get collage
        _username = aCtx.user.name
        _title = f'Build for user {_username}'
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)
        
        # Save collage
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath, self.__userId)
        _image = File(_imagePath)
        
        # Log end of method
        mLogInfo(f'Random build provided for user {self.__userId}')
        # Return build names and images
        return _buildNames, _image

    def mAddToBlackList(self, aPerkId: str) -> None:
        # Add perk to blacklist
        self.__tracker.mAddPerkToBlackList(aPerkId)

        # Log action
        _name = self.__tracker.mGetPerkName(aPerkId)
        _msg = f'Perk {_name} added to blacklist for user {self.__userId}'
        mLogInfo(_msg)

    def mRemoveFromBlackList(self, aPerkId: str) -> None:
        # Remove perk from blacklist
        self.__tracker.mRemovePerkFromBlackList(aPerkId)
        # Log action
        _name = self.__tracker.mGetPerkName(aPerkId)
        _msg = f'Perk {_name} removed from blacklist for user {self.__userId}'
        mLogInfo(_msg)

    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> tuple[list[str], File]:
        # Get last roll
        _lastRoll = self.__tracker.mGetLastRoll()
        
        # Check if there are perks to replace
        if len(_lastRoll) < self.__tracker.BUILD_SIZE:
            raise ValueError('No perks to replace')
        
        # Get new valid perk and update last roll
        _newPerk = self.__tracker.mGetRandomValidPerk()
        _lastRoll[aPerkIndex] = _newPerk
        self.__tracker.mUpdateLastRoll(_lastRoll)
        _buildNames = [self.__tracker.mGetPerkName(_id) for _id in _lastRoll]
        
        # Make new collage
        _username = aCtx.user.name
        _images = self.__tracker.mGetImages(_lastRoll)
        _title = f'Build for user {_username}'
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)

        # Save collage
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath, self.__userId)
        _image = File(_imagePath)

        return _buildNames, _image

    def mGetWhitelistedPerkNames(self) -> list:
        return self.__tracker.mGetWhitelistedPerkNames()

    def mGetBlacklistedPerkNames(self) -> list:
        return [self.__tracker.mGetPerkName(_id) for _id in self.__tracker.mGetBlackList()]

    def mGetPerkNames(self) -> list:
        return self.__tracker.mGetAllPerkNames()

    def mGetPerkName(self, aId: str) -> str:
        return self.__tracker.mGetPerkName(aId)

    def mGetHelp(self, aId: str) -> str:
        # Get description
        _description: dict = self.__tracker.mGetDescription(aId)

        # Format description
        _name = self.__tracker.mGetPerkName(aId)
        _body = ""
        for _key in _description:
            _line = _description.get(_key)
            if len(_line) > 0:
                _body += f"{_description.get(_key)}\n"

        # Return formatted description
        return f'--- ***{_name.upper()}*** ---\n{_body}'

    def mGetPerkImage(self, aPerkId: str) -> File:
        # Get image path
        _imagePath = self.__tracker.mGetImage(aPerkId)
        return File(_imagePath)

    def mGetPerkIdByName(self, aPerkName: str) -> str:
        return self.__tracker.mGetPerkIdByName(aPerkName)

    def mGetPerkIdFromBuild(self, aPerkIndex: int) -> str:
        _lastRoll = self.__tracker.mGetLastRoll()
        return _lastRoll[aPerkIndex]

    def mRegisterResult(self, aWin: bool, aPerkIds: list[str]) -> None:        
        # For each perk in last roll, increment the counts in both CSVs
        _columns =['games'] + ['escapes'] if aWin else ['deaths']
        _lastRoll = aPerkIds
        # Register escape in user data
        mLogInfo(f'Registering win with perk {_lastRoll}')
        self.__userDataHandler.mIncrementColumns(_lastRoll, _columns, [1, 1])
        
        # Register escape in general data
        self.__dataHandler.mIncrementColumns(_lastRoll, _columns, [1, 1])

        mLogInfo('Saved user and general record CSVs')

    def mSetCustomBuild(self, aCtx: Interaction, aBuild: list) -> tuple:
        # Set last roll and generate new collage
        self.__tracker.mSetLastRoll(aBuild)
        _collage = self.mGenerateCollage(aCtx, self.__tracker.mGetLastRoll())
        # Log and return
        _names = [self.__tracker.mGetPerkName(_id) for _id in self.__tracker.mGetLastRoll()]
        return _names, _collage

    def mGetUsageGraph(self, aUserId: str | None = None) -> File:
        # Get template CSV
        _templatePath = mGetFile('assets/dbd/data/templates/dbdperkusage_template.csv')
        # Get user CSV file
        _csvPath = os.path.join(mGetDBDDataDir(), 'dbdperkusage.csv')
        if aUserId:
            _csvPath = os.path.join(mGetDBDDataDir(), 'generated', f'{aUserId}_dbdperkusage.csv')
        _csvFile = mEnsureFile(_csvPath, _templatePath)
        mLogInfo("Loaded data from CSV at " + _csvFile)

        # Load CSV data
        _imagePath = self.__dataHandler.mPlotClusterHeatmap()
        return File(_imagePath)

    def mRandomizeCSVData(self) -> None:
        self.__userDataHandler.mRandomizeResults(52, 250)
        mLogInfo(f'Randomized CSV data for user {self.__userId}')

    def mResetCSVData(self) -> None:
        self.__userDataHandler.mResetResults()
        mLogInfo(f'Reset CSV data for user {self.__userId}')