# Generic imports
import os
import random

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mParseJsonFile, mGetConfigDir, mWriteJsonFile, mMakeUserFile

class PerkTracker:
    """
    Helper class to keep track of perk instances per user.
    """
    # Set constants
    MAX_PERK_COUNT = 5
    BUILD_SIZE = 4
    TITLE = 'title'
    CHARACTER = 'character'
    DESCRIPTION = 'description'
    IMG = 'img'
    MAIN_EFFECT = 'mainEffect'
    SECONDARY_EFFECT = 'secondaryEffect'
    ADDITIONAL_EFFECT = 'additionalEffect'
    
    # Set class paths
    __configDir = mGetConfigDir()
    __perksPath = os.path.join(__configDir, 'dbdperks.json')

    # Load dicts from JSON files
    __perks = mParseJsonFile(__perksPath)
    
    def __init__(self, aUserId: str, aUserName: str) -> None:
        # Set owner
        self.__userId = int(aUserId)
        self.__userName = aUserName
        # Set perk tracking variables
        self.__tracker = {}
        self.__lastRoll = []
        self.__lastBuildId = None
        self.__lastMessage = None
        # Set black list
        self.__blacklistPath = os.path.join(self.__configDir, 'dbdblacklist.json')
        self.__blacklist = self.mLoadBlackList()

    def mSetLastBuildId(self, aBuildId: int) -> None:
        self.__lastBuildId = aBuildId
        mLogInfo(f'Last build id set for user {self.__userId}: {aBuildId}')

    def mGetLastBuildId(self) -> int:
        return self.__lastBuildId

    def mUpdateTracker(self, aPerkId: str) -> None:
        # Check if perk is in tracker
        if aPerkId not in self.__tracker:
            self.__tracker[aPerkId] = 1
            mLogInfo(f'Perk {aPerkId} added to tracker for user {self.__userId}')
            return
        # If perk is already at 5, in which case it is removed.
        if self.__tracker[aPerkId] >= self.MAX_PERK_COUNT:
            self.__tracker.pop(aPerkId)
            mLogInfo(f'Perk {aPerkId} removed from tracker for user {self.__userId}')
            return
        # Increment perk count
        self.__tracker[aPerkId] += 1
        mLogInfo(f'Perk {aPerkId} count updated to {self.__tracker[aPerkId]} for user {self.__userId}')

    def mIsRepeated(self, aPerkId: str) -> bool:
        _result = aPerkId in self.__tracker
        if _result:
            mLogInfo(f'Perk {aPerkId} is repeated for user {self.__userId}')
        return _result

    def mUpdateLastRoll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll
        mLogInfo(f'Last roll updated for user {self.__userId}. Roll: {aRoll}')

    def mGetLastRoll(self) -> list:
        return self.__lastRoll

    def mSetLastMessage(self, aMessage: str) -> None:
        self.__lastMessage = aMessage
        mLogInfo(f'Last message id set for user {self.__userId}: {aMessage}')

    def mGetLastMessage(self) -> str:
        return self.__lastMessage

    def mGetPerkId(self, aPerk: dict) -> str:
        # Get keys of perk
        _keys = list(aPerk.keys())
        # Get first element since it is the only key
        return _keys[0]

    def mGetPerkIdByName(self, aPerkName: str) -> str:
        # Get perk id by name
        for _perkId in self.__perks:
            _perk = self.__perks[_perkId]
            if _perk[self.TITLE] == aPerkName:
                return _perkId
        mLogError(f'Perk {aPerkName} not found')
        raise ValueError(f'Perk {aPerkName} not found')

    def mGetPerkName(self, aPerkId: str) -> str:
        _perk = self.__perks[aPerkId]
        return _perk[self.TITLE]

    def mGetBlackList(self) -> set:
        return self.__blacklist

    def mLoadBlackList(self) -> set:
        # Check if blacklist file exists
        if not os.path.exists(self.__blacklistPath):
            mWriteJsonFile(self.__blacklistPath, {})
        # Get user blacklist
        _blacklist = mParseJsonFile(self.__blacklistPath)
        _userBlacklist = _blacklist.get(self.__userName, [])
        # Return user blacklist as a set
        mLogInfo(f'Blacklist loaded for user {self.__userName}: {_userBlacklist}')
        return set(_userBlacklist)

    def mIsBlacklisted(self, aPerkId: str) -> bool:
        _result = aPerkId in self.__blacklist
        if _result:
            mLogInfo(f'Perk {aPerkId} is blacklisted for user {self.__userName}')
        return _result

    def mUpdateBlackListFile(self) -> None:
        # Save updated blacklist
        _blacklist = mParseJsonFile(self.__blacklistPath)
        _blacklist[self.__userName] = list(self.__blacklist)
        mLogInfo(f'Current blacklist for user {self.__userName}: {_blacklist}')
        mWriteJsonFile(self.__blacklistPath, _blacklist)
        mLogInfo(f'Blacklist updated for user {self.__userName}')

    def mAddPerkToBlackList(self, aPerkId: str) -> None:
        # Check if perk is already blacklisted
        if self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is already blacklisted for user {self.__userName}')
            return
        # Add perk to blacklist
        self.__blacklist.add(aPerkId)
        # Save updated blacklist
        self.mUpdateBlackListFile()

    def mRemovePerkFromBlackList(self, aPerkId: str) -> None:
        # Check if perk is blacklisted
        if not self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is not blacklisted for user {self.__userName}')
            return
        # Remove perk from blacklist
        self.__blacklist.remove(aPerkId)
        mLogInfo(f'Perk {self.mGetPerkName(aPerkId)} removed from blacklist for user {self.__userName}')
        # Save updated blacklist
        self.mUpdateBlackListFile()

    def mIsValid(self, aPerkId: str) -> bool:
        return not self.mIsBlacklisted(aPerkId) and not self.mIsRepeated(aPerkId)

    def mGetRandomPerkId(self) -> str:
        # Get random perk
        _perkId = random.choice(list(self.__perks.keys()))
        mLogInfo(f'Random perk {self.mGetPerkName(_perkId)} selected for user {self.__userName}')
        return _perkId

    def mGetRandomValidPerk(self) -> str:
        # Get random perk
        _perkId = self.mGetRandomPerkId()

        # Check if perk is blacklisted
        while not self.mIsValid(_perkId):
            self.mUpdateTracker(_perkId)
            mLogError(f'Perk {self.mGetPerkName(_perkId)} is blacklisted or repeated for user {self.__userId}. Getting another perk')
            _perkId = self.mGetRandomPerkId()

        # Get all the information of the perk
        self.mUpdateTracker(_perkId)
        mLogInfo(f'Valid perk {self.mGetPerkName(_perkId)} selected for user {self.__userId}')
        return _perkId

    def mGetRoll(self) -> list:
        # Get random perks
        _roll = []
        for _ in range(self.BUILD_SIZE):
            _perk = self.mGetRandomValidPerk()
            _roll.append(_perk)
        # Update last roll
        self.mUpdateLastRoll(_roll)
        return _roll

    def mGetImage(self, aPerkId: str) -> str:
        # Check if perk exists
        if not aPerkId in self.__perks:
            _err_msg = f'Perk {aPerkId} not found'
            mLogError(_err_msg)
            raise ValueError(_err_msg)
        # Get image path
        _path = self.__perks[aPerkId][self.IMG]
        mLogInfo(f'Image path for perk {self.mGetPerkName(aPerkId)} retrieved: {_path}')
        return _path

    def mGetDescription(self, aPerkId: str) -> dict:
        # Check if perk exists
        if not aPerkId in self.__perks:
            _err_msg = f'Perk {aPerkId} not found'
            mLogError(_err_msg)
            raise ValueError(_err_msg)
        # Get description
        _description = self.__perks[aPerkId][self.DESCRIPTION]
        mLogInfo(f'Description for perk {self.mGetPerkName(aPerkId)} retrieved.')
        return _description

    def mGetImages(self, aPerkIds: list[str]) -> list[str]:
        # Set images list
        _images = []
        # Try to get images
        try:
            for _perkId in aPerkIds:
                _images.append(self.mGetImage(_perkId))
            return _images
        except ValueError as e:
            mLogError(f'Error during image retrieval: {e}')
            return []

    def mGetWhitelistedPerkNames(self) -> dict:
        return [_perk.get(self.TITLE) for _id, _perk in self.__perks.items() if not self.mIsBlacklisted(_id)]

    def mGetAllPerkNames(self) -> list:
        return [_perk.get(self.TITLE) for _perk in self.__perks.values()]

    def mSetLastRoll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll
        mLogInfo(f'Last roll set for user {self.__userId}. Roll: {aRoll}')