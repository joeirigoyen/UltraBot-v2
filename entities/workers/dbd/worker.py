# Generic imports
import os
import random

# Specific imports
from discord import File, Interaction

# Custom imports
from log.logger import mLogError, mLogInfo, mLogDebug
from entities.utils.datahandler import mLoadCsvData, mIncrementColumn, mSaveCsvData, mCreateUsageGraph
from entities.utils.files import mCleanupDir, mGetAssetsDir, mGetDBDConfig, mGetDBDDataDir, mGetFile, mEnsureFile
from entities.utils.images import mCreateCollage, mSaveImage
from entities.workers.dbd.perks import PerkTracker, Perk


class DbdWorker():

    __assetsDir = mGetAssetsDir()
    __dbdAssetsDir = os.path.join(__assetsDir, 'dbd')
    __dbdGenImagesDir = os.path.join(__dbdAssetsDir, 'imgs', 'generated')

    def __init__(self, aCtx: Interaction):
        # Set owner
        self.__userId = aCtx.user.id
        self.__userName = aCtx.user.name
        # Get blacklist from config
        self.__tracker = PerkTracker(self.__userId, self.__userName)
        # Log worker creation
        mLogInfo(f'Worker {self.__userId} created')

    def mGetUserBlackList(self) -> set:
        return self.__tracker.mGetBlackList()

    def mGenerateCollage(self, aCtx: Interaction, aBuild: list[Perk]) -> File:
        # For each perk in aBuild, get the image
        _images = [_perk.img for _perk in aBuild]
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
        _buildNames = [_perk.title for _perk in _build]
        _images = [_perk.img for _perk in _build]
        
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

    def mAddToBlackList(self, aPerk: Perk) -> str:
        # Add perk to blacklist
        self.__tracker.mAddPerkToBlackList(aPerk)

        # Log action
        _name = aPerk.title
        _msg = f'Perk {_name} added to blacklist for user {self.__userId}'
        mLogInfo(_msg)

    def mRemoveFromBlackList(self, aPerk: Perk) -> str:
        # Remove perk from blacklist
        self.__tracker.mRemovePerkFromBlackList(aPerk)
        # Log action
        _name = self.__tracker.mGetPerkNameById(aPerk)
        _msg = f'Perk {_name} removed from blacklist for user {self.__userId}'
        mLogInfo(_msg)

    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> str:
        # Get last roll
        _lastRoll = self.__tracker.last_roll
        
        # Check if there are perks to replace
        if len(_lastRoll) < self.__tracker.BUILD_SIZE:
            raise ValueError('No perks to replace')
        
        # Get new valid perk and update last roll
        _newPerk = self.__tracker.mGetRandomValidPerk()
        _lastRoll[aPerkIndex] = _newPerk
        self.__tracker.last_roll = _lastRoll
        _buildNames = [_perk.title for _perk in _lastRoll]
        
        # Make new collage
        _username = aCtx.user.name
        _images = [_perk.img for _perk in _lastRoll]
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
        return self.__tracker.mGetBlacklistedPerkNames()

    def mGetPerkNames(self) -> list:
        return self.__tracker.mGetAllPerkNames()

    def mGetPerkName(self, aId: str) -> str:
        return self.__tracker.mGetPerkNameById(aId)

    def mGetHelp(self, aPerk: Perk) -> str:
        # Get description
        _description: dict = aPerk.description

        # Format description
        _name = self.__tracker.mGetPerkNameById(aPerk)
        _body = ""
        for _key in _description:
            _line = _description.get(_key)
            if len(_line) > 0:
                _body += f"{_description.get(_key)}\n"

        # Return formatted description
        return f'--- ***{_name.upper()}*** ---\n{_body}'

    def mGetPerkImage(self, aPerkId: str) -> str:
        # Get image path
        _imagePath = self.__tracker.mGetImage(aPerkId)
        return File(_imagePath)

    def mGetPerkIdByName(self, aPerkName: str) -> str:
        return self.__tracker.mGetPerkIdByName(aPerkName)

    def mGetPerkIdFromBuild(self, aPerkIndex: int) -> str:
        _lastRoll = self.__tracker.mGetLastRoll()
        return _lastRoll[aPerkIndex]

    def mRegisterWin(self) -> None:
        # Load user's record CSV
        _userCsvFile = os.path.join(mGetDBDDataDir(), 'generated', f'{self.__userId}_dbdperkusage.csv')
        mLogInfo('Loaded user record CSV')
        
        # Load general record CSV
        _generalCsvFile = os.path.join(mGetDBDDataDir(), 'dbdperkusage.csv')
        mLogInfo('Loaded general record CSV')
        
        # Load user and general stats
        _lastRoll = self.__tracker.mGetLastRoll()
        _userData = mLoadCsvData(_userCsvFile)
        _generalData = mLoadCsvData(_generalCsvFile)
        
        # For each perk in last roll, increment the counts in both CSVs
        for _perkId in _lastRoll:
            # Register escape in user data
            mLogInfo(f'Registering win with perk {_perkId}')
            _userData = mIncrementColumn(_userData, 'games', 'id', _perkId)
            _userData = mIncrementColumn(_userData, 'escapes', 'id', _perkId)
            
            # Register escape in general data
            _generalData = mIncrementColumn(_generalData, 'games', 'id', _perkId)
            _generalData = mIncrementColumn(_generalData, 'escapes', 'id', _perkId)
        
        # Save the updated CSVs
        mSaveCsvData(_userData, _userCsvFile)
        mSaveCsvData(_generalData, _generalCsvFile)
        mLogInfo('Saved user and general record CSVs')

    def mRegisterLoss(self) -> None:
        # Load user's record CSV
        _userCsvFile = os.path.join(mGetDBDDataDir(), 'generated', f'{self.__userId}_dbdperkusage.csv')
        mLogInfo('Loaded user record CSV')
        
        # Load general record CSV
        _generalCsvFile = os.path.join(mGetDBDDataDir(), 'dbdperkusage.csv')
        mLogInfo('Loaded general record CSV')
        
        # Load user and general stats
        _lastRoll = self.__tracker.mGetLastRoll()
        _userData = mLoadCsvData(_userCsvFile)
        _generalData = mLoadCsvData(_generalCsvFile)
        
        # For each perk in last roll, increment the counts in both CSVs
        for _perkId in _lastRoll:
            # Register escape in user data
            mLogInfo(f'Registering loss with perk {_perkId}')
            _userData = mIncrementColumn(_userData, 'games', 'id', _perkId)
            _userData = mIncrementColumn(_userData, 'deaths', 'id', _perkId)
            
            # Register escape in general data
            _generalData = mIncrementColumn(_generalData, 'games', 'id', _perkId)
            _generalData = mIncrementColumn(_generalData, 'deaths', 'id', _perkId)
        
        # Save the updated CSVs
        mSaveCsvData(_userData, _userCsvFile)
        mSaveCsvData(_generalData, _generalCsvFile)
        mLogInfo('Saved user and general record CSVs')

    def mSetCustomBuild(self, aCtx: Interaction, aBuild: list) -> tuple:
        # Set last roll and generate new collage
        self.__tracker.mSetLastRoll(aBuild)
        _collage = self.mGenerateCollage(aCtx, self.__tracker.mGetLastRoll())
        # Log and return
        _names = [self.__tracker.mGetPerkNameById(_id) for _id in self.__tracker.mGetLastRoll()]
        return _names, _collage

    def mGetUsageGraph(self, aUser: str = None, aPerk: str = None) -> str:
        # Get template CSV
        _templatePath = mGetFile('assets/dbd/data/templates/dbdperkusage_template.csv')
        # Get user CSV
        if aUser is not None:
            _csvPath = os.path.join(mGetDBDDataDir(), 'generated', f'{aUser}_dbdperkusage.csv')
        else:
            _csvPath = os.path.join(mGetDBDDataDir(), 'dbdperkusage.csv')
        _csvFile = mEnsureFile(_csvPath, _templatePath)
        # Get image path
        _user = aUser if aUser is not None else 'General'
        _title = f'Perk Usage Graph ({_user})'
        # Load CSV data
        _data = mLoadCsvData(_csvFile)
        _imagePath = mCreateUsageGraph(_data, _title, aUser=_user, aPerk=aPerk)
        return File(_imagePath)

    def mRandomizeCSVData(self) -> None:
        _csvPath = os.path.join(mGetDBDDataDir(), 'generated', f'{self.__userId}_dbdperkusage.csv')
        _csvFile = mGetFile(_csvPath)
        # Load CSV data
        _data = mLoadCsvData(_csvFile)
        # Randomize data values for escapes and deaths
        _data['escapes'] = _data['escapes'].apply(lambda x: x * 0 + random.randint(10, 100))
        _data['deaths'] = _data['deaths'].apply(lambda x: x * 0 + random.randint(10, 100))
        # Sum games using escapes and deaths
        _data['games'] = _data['escapes'] + _data['deaths']
        # Save CSV data
        mSaveCsvData(_data, _csvFile)
        mLogInfo(f'Randomized CSV data for user {self.__userId}')

    def mResetCSVData(self) -> None:
        _csvPath = os.path.join(mGetDBDDataDir(), 'generated', f'{self.__userId}_dbdperkusage.csv')
        _csvFile = mGetFile(_csvPath)
        # Load CSV data
        _data = mLoadCsvData(_csvFile)
        # Reset data values for escapes and deaths
        _data['escapes'] = _data['escapes'].apply(lambda x: x * 0)
        _data['deaths'] = _data['deaths'].apply(lambda x: x * 0)
        # Sum games using escapes and deaths
        _data['games'] = _data['escapes'] + _data['deaths']
        # Save CSV data
        mSaveCsvData(_data, _csvFile)
        mLogInfo(f'Reset CSV data for user {self.__userId}')