# Generic imports
import os
import random

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mGetConfigProperty
from entities.utils.rare import mSuperCleanString

class PerkTracker:
    """
    Helper class to keep track of perk instances per user.
    """
    # Set constants
    MAX_PERK_COUNT = 5
    BUILD_SIZE = 4
    TITLE = 'name'
    CHARACTER = 'owner_name'
    DESCRIPTION = 'main_effect'
    
    def __init__(self, aUserId: str, aUserName: str, aPerks: list) -> None:
        # Set owner
        self.__userId = int(aUserId)
        self.__userName = aUserName
        self.__perks: list[dict] = aPerks
        # Set perk tracking variables
        self.__tracker = {}
        self.__lastRoll = []
        self.__lastBuildId = None
        self.__lastMessage = None
        # Set black list
        self.__blacklist = None

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

    def mGetBlackList(self) -> set:
        # Return blacklist cache
        return self.__blacklist

    def mSetBlackList(self, aBlacklist: set) -> None:
        # Update blacklist cache
        self.__blacklist = aBlacklist

    def mIsBlacklisted(self, aPerkId: str) -> bool:
        _result = aPerkId in self.__blacklist
        if _result:
            mLogInfo(f'Perk {aPerkId} is blacklisted for user {self.__userName}')
        return _result

    def mAddPerkToBlackList(self, aPerkId: str) -> None:
        # Check if perk is already blacklisted
        if self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is already blacklisted for user {self.__userName}')
            return
        # Add perk to blacklist
        self.__blacklist.add(aPerkId)

    def mRemovePerkFromBlackList(self, aPerkId: str) -> None:
        # Check if perk is blacklisted
        if not self.mIsBlacklisted(aPerkId):
            mLogError(f'Perk {aPerkId} is not blacklisted for user {self.__userName}')
            return
        # Remove perk from blacklist
        self.__blacklist.remove(aPerkId)
        mLogInfo(f'Perk {aPerkId} removed from blacklist for user {self.__userName}')

    def mIsValid(self, aPerkId: str) -> bool:
        return not self.mIsBlacklisted(aPerkId) and not self.mIsRepeated(aPerkId)

    def mGetRandomPerkId(self) -> str:
        # Get random perk from list
        _perk = random.choice(self.__perks)
        # Get perk name from perk 
        _perkId = _perk.get(self.TITLE)
        mLogInfo(f'Random perk {_perkId} selected for user {self.__userName}')
        return _perkId

    def mGetRandomValidPerk(self) -> str:
        # Get random perk
        _perkId = self.mGetRandomPerkId()

        # Check if perk is blacklisted
        while not self.mIsValid(_perkId):
            self.mUpdateTracker(_perkId)
            mLogError(f'Perk {_perkId} is blacklisted or repeated for user {self.__userId}. Getting another perk')
            _perkId = self.mGetRandomPerkId()

        # Get all the information of the perk
        self.mUpdateTracker(_perkId)
        mLogInfo(f'Valid perk {_perkId} selected for user {self.__userId}')
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

    @staticmethod
    def mGetImage(aPerkId: str) -> str:
        # Get clean perk name
        _perkName = mSuperCleanString(aPerkId)
        # Get image path
        _imgDir = mGetConfigProperty('PERKS_IMG_DIR')
        if not _imgDir:
            mLogError("Could not retrieve property 'PERKS_IMG_DIR' from config")
        _imgPath = os.path.join(_imgDir, f'{_perkName}.png')
        # Check if perk exists
        if not os.path.exists(_imgPath):
            _err_msg = f'Image {_imgPath} not found'
            mLogError(_err_msg)
            return os.path.join(_imgDir, f'notfound.png')
        # Get image path
        mLogInfo(f'Image path for perk {aPerkId} retrieved: {_imgPath}')
        return _imgPath

    def mGetDescription(self, aPerkId: str) -> str:
        # Get description
        for _perk in self.__perks:
            if _perk.get(self.TITLE) == aPerkId:
                _description = _perk.get(self.DESCRIPTION)
                mLogInfo(f'Description for perk {aPerkId} retrieved.')
                return _description
        mLogInfo(f'Description for perk {aPerkId} not found.')

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

    def mGetWhitelistedPerkNames(self) -> list[str]:
        _perks = [_perk[self.TITLE] for _perk in self.__perks if not self.mIsBlacklisted(_perk['name'])]
        return _perks

    def mGetAllPerkNames(self) -> list:
        _perks = [_perk[self.TITLE] for _perk in self.__perks]
        return _perks

    def mSetLastRoll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll
        mLogInfo(f'Last roll set for user {self.__userId}. Roll: {aRoll}')