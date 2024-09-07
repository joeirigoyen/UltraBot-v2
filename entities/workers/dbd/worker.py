# Generic imports
import os

# Specific imports
from discord import File, Interaction
from datetime import datetime, timedelta

# Custom imports
from log.logger import mLogInfo
from entities.utils.datahandler import DBDDataHandler
from entities.utils.files import mGetAssetsDir, mGetConfigProperty
from entities.utils.images import mCreateCollage, mSaveImage
from entities.utils.sql import SQLRetriever
from entities.workers.dbd.perks import PerkTracker


class DbdWorker:

    __assetsDir = mGetAssetsDir()
    __dbdAssetsDir = os.path.join(__assetsDir, 'dbd')
    __dbdGenImagesDir = mGetConfigProperty("GENERATED_IMG_DIR")

    def __init__(self, aCtx: Interaction):
        # Set owner
        self.__userId = str(aCtx.user.id)
        self.__userName = aCtx.user.name
        # Get last database update
        self.__sql = SQLRetriever()
        self.__lastDbUpdate = datetime.now()
        self.__sql.mAddUser(self.__userId, self.__userName)
        # Get blacklist from config
        self.__perks = self.mGetAllPerks()
        mLogInfo(f"Perks: {self.__perks}")
        self.__tracker = PerkTracker(self.__userId, self.__userName, self.__perks)
        self.mLoadUserBlackListFromDB()
        # Load data handler
        self.__dataHandler = DBDDataHandler()
        # Log worker creation
        mLogInfo(f'Worker {self.__userId} created')

    @property
    def userId(self):
        return self.__userId
    
    @property
    def userName(self):
        return self.__userName

    def mGetAllPerks(self) -> list[dict]:
        return self.__sql.mGetAllPerksBasicInfo()

    def mGetUserBlackList(self) -> set:
        _blacklist = self.__tracker.mGetBlackList()
        if not _blacklist:
            mLogInfo(f'Blacklist not found for user {self.__userId}, loading from DB.')
            self.mLoadUserBlackListFromDB()
            _blacklist = self.__tracker.mGetBlackList()
        return _blacklist

    def mLoadUserBlackListFromDB(self) -> None:
        _blackList = self.__sql.mGetBlackList(self.__userId)
        self.__tracker.mSetBlackList(_blackList)
        mLogInfo(f'Blacklist loaded from DB for user {self.__userId}')

    def mUpdateUserBlackList(self, aForce: bool = False) -> None:
        # Check time since last update
        _maxUpdateTime = int(mGetConfigProperty('DBD_DB_UPDATE_MINS'))
        _currentTime = datetime.now()
        if not (_currentTime - self.__lastDbUpdate).min >= timedelta(_maxUpdateTime) and not aForce:
            mLogInfo(f"Skipping DB update for user {self.__userId}")
            return
        # Update blacklist to DB
        self.__lastDbUpdate = _currentTime
        _currentBlackList = self.__tracker.mGetBlackList()
        self.__sql.mUpdateBlackList(self.__userId, _currentBlackList)
        mLogInfo(f'Blacklist updated in DB for user {self.__userId}')

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
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'{_username}_randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath)
        return File(_imagePath)

    def mGetRandomBuild(self, aCtx: Interaction) -> tuple[list[str], File]:
        # Log start of method
        mLogInfo(f'Random build requested for user {self.__userId}')
        
        # Get four random perks
        _build = self.__tracker.mGetRoll()

        # Get collage
        _image = self.mGenerateCollage(aCtx, _build)        
        
        # Log end of method
        mLogInfo(f'Random build provided for user {self.__userId}')

        # Return build names and images
        return _build, _image

    def mAddToBlackList(self, aPerkId: str) -> str:
        # Add perk to blacklist
        self.__tracker.mAddPerkToBlackList(aPerkId)

        # Log action
        _msg = f'Perk {aPerkId} added to blacklist for user {self.__userId}'
        mLogInfo(_msg)
        
        # Update to DB if needed
        self.mUpdateUserBlackList()
        return _msg

    def mRemoveFromBlackList(self, aPerkId: str) -> str:
        # Remove perk from blacklist
        self.__tracker.mRemovePerkFromBlackList(aPerkId)
        # Log action
        _msg = f'Perk {aPerkId} removed from blacklist for user {self.__userId}'
        mLogInfo(_msg)
        # Update to DB if needed
        self.mUpdateUserBlackList()
        return _msg

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
        
        # Make new collage
        _username = aCtx.user.name
        _images = self.__tracker.mGetImages(_lastRoll)
        _title = f'Build for user {_username}'
        _collage = mCreateCollage(_images, 800, 160, aTitle=_title)

        # Save collage
        _collagePath = os.path.join(self.__dbdGenImagesDir, f'randombuild.png')
        _imagePath = mSaveImage(_collage, _collagePath)
        _image = File(_imagePath)

        return _lastRoll, _image

    def mGetWhitelistedPerkNames(self) -> list:
        return self.__tracker.mGetWhitelistedPerkNames()

    def mGetBlacklistedPerkNames(self) -> set:
        return self.__tracker.mGetBlackList()

    def mGetPerkNames(self) -> list:
        return self.__tracker.mGetAllPerkNames()

    def mGetHelp(self, aId: str) -> str:
        # Get description
        _description = self.__tracker.mGetDescription(aId)
        _description = _description.split('.')

        # Format description
        _body = ""
        for _paragraph in _description:
            _body += f"{_paragraph}\n"

        # Return formatted description
        return f'--- ***{aId.upper()}*** ---\n{_body}'

    def mGetPerkImage(self, aPerkId: str) -> File:
        # Get image path
        _imagePath = self.__tracker.mGetImage(aPerkId)
        return File(_imagePath)

    def mGetPerkFromBuild(self, aPerkIndex: int) -> str:
        _lastRoll = self.__tracker.mGetLastRoll()
        return _lastRoll[aPerkIndex]

    def mRegisterResult(self, aWin: bool, aPerkNames: list[str]) -> None:        
        # Prepare data for DB push
        _data = {
            "userId": int(self.__userId),
            "matchResult": 'ESCAPE' if aWin else 'DEATH',
            "matchDate": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "perkNames": aPerkNames
        }
        # Register escape in user data
        self.__sql.mRegisterMatchResult(_data)
        mLogInfo(f'Registered win with perks {aPerkNames} for user {self.__userId}')

    def mSetCustomBuild(self, aCtx: Interaction, aBuild: list) -> tuple:
        # Set last roll and generate new collage
        self.__tracker.mSetLastRoll(aBuild)
        _collage = self.mGenerateCollage(aCtx, self.__tracker.mGetLastRoll())
        # Log and return
        _names = self.__tracker.mGetLastRoll()
        return _names, _collage

    def mGetUsageGraph(self, aOrder: str = 'most', aUser: int = None, aLimit: int = 10) -> File:
        # Get SQL results
        _results, _columns = self.__sql.mGetPerkUsage(aOrder, aUser, aLimit)
        mLogInfo(f"Results: {_results}")
        # Get path of image
        _date = datetime.now().strftime('%Y-%m-%d')
        _userStr = str(aUser) if aUser else "all"
        _imgName = f"{_date}_{_userStr}_perks_usage.png"
        _imgDir = mGetConfigProperty("GENERATED_IMG_DIR")
        _imgPath = os.path.join(_imgDir, _imgName)
        # Pass results to a new data handler
        _title = f"Perk Usage Plot"
        self.__dataHandler.mLoadAndCleanData(_results)
        self.__dataHandler.mCreateBarPlot(_columns[0], _columns[1], _imgPath, aTitle=_title)
        return File(_imgPath)

    def mKillSQLRetriever(self) -> None:
        del self.__sql
        mLogInfo("Closed SQL connection")
