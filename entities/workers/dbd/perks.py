# Generic imports
import os
import random

# Specific imports
from typing import Literal

# Custom imports
from log.logger import mLogError, mLogInfo
from entities.utils.files import mParseJsonFile, mGetConfigDir, mWriteJsonFile, mMakeUserFile

class Perk:
    """
    Defines a perk with its attributes.
    """
    
    MAX_PERK_COUNT = 5
    
    def __init__(self, aPerkId: str, aInfo: dict) -> None:
        # Set perk attributes
        self.__id: str = aPerkId
        self.__info: dict = aInfo
        self.__blacklisted = False
        self.__uses = 0

    def __eq__(self, aOther) -> bool:
        if isinstance(aOther, Perk):
            return self.id == aOther.id
        elif isinstance(aOther, str):
            return self.id == aOther
        elif isinstance(aOther, dict):
            return self.id == aOther.get('id')

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.title} from {self.character} with id {self.id}"

    def __str__(self) -> str:
        return self.title

    @property
    def id(self) -> str:
        return self.__id

    @property
    def title(self) -> str:
        return self.__info.get('title')
    
    @property
    def character(self) -> str:
        return self.__info.get('character')
    
    @property
    def description(self) -> dict:
        return self.__info.get('description')

    @property
    def long_description(self) -> str:
        return self.mFormatDescription()

    @property
    def main_effect(self) -> str:
        return self.description.get('mainEffect')

    @property
    def secondary_effect(self) -> str:
        return self.description.get('secondaryEffect')

    @property
    def additional_effect(self) -> str:
        return self.description.get('additionalEffect')

    @property
    def img(self) -> str:
        return self.__info.get('img')

    @property
    def uses(self) -> int:
        return self.__uses

    @uses.setter
    def uses(self, aUses: int) -> None:
        self.__uses = aUses

    def mFormatDescription(self) -> str:
        # Set formatted description
        _string = f"*** --- {self.title} --- ***\n"
        for _key, _val in self.description.items():
            _string += f"- **{_key}:** *{_val}*\n"
        return _string

    def mBlacklist(self) -> None:
        self.__blacklisted = True

    def mUnblacklist(self) -> None:
        self.__blacklisted = False

    def mIsBlacklisted(self) -> bool:
        return self.__blacklisted

    def mIsRepeated(self) -> bool:
        return self.__uses >= 1

    def mIsValid(self) -> bool:
        return not self.mIsBlacklisted() and not self.mIsRepeated()

    def mUpdateUses(self) -> None:
        # If perk is already at 5, in which case it is removed.
        if self.uses >= self.MAX_PERK_COUNT:
            self.uses = 0
            mLogInfo(f'Perk {self.title} uses set to 0')
            return
        # Increment perk count
        self.uses += 1
        mLogInfo(f'Perk {self.title} count updated to {self.uses}')

class PerkTracker:
    """
    Helper class to keep track of perk instances per user.
    """
    # Set constants
    BUILD_SIZE = 4
    
    # Set class paths
    __configDir = mGetConfigDir()
    __perksPath = os.path.join(__configDir, 'dbdperks.json')
    __spanishPerksPath = os.path.join(__configDir, 'dbdperks_es.json')
    
    def __init__(self, aUserId: str, aUserName: str) -> None:
        # Set owner
        self.__userid = int(aUserId)
        self.__username = aUserName
        # Set perklist
        self.__perks: set[Perk] = self.mLoadPerks()
        # Set perk tracking variables
        self.__lastRoll = []
        # Set black list
        self.__blacklistPath = os.path.join(self.__configDir, 'dbdblacklist.json')
        self.__blacklist = self.mLoadBlackList()
        # Update blacklisted perks
        self.mUpdateBlacklistStatus()

    @property
    def userid(self) -> int:
        return self.__userid
    
    @property
    def username(self) -> str:
        return self.__username

    @property
    def last_roll(self) -> list[Perk]:
        return self.__lastRoll

    @last_roll.setter
    def last_roll(self, aRoll: list) -> None:
        self.__lastRoll = aRoll

    def mGetPerksDict(self, aLanguage: Literal['en', 'es'] = 'en') -> dict:
        # Get perk file based on language
        match aLanguage:
            case 'en':
                _perkInfo = mParseJsonFile(self.__perksPath)
            case 'es':
                _perkInfo = mParseJsonFile(self.__spanishPerksPath)
            case _:
                mLogError(f'Language {aLanguage} not supported')
                raise ValueError(f'Language {aLanguage} not supported')
        return _perkInfo

    def mLoadPerks(self, aLanguage: Literal['en', 'es'] = 'en') -> set:
        # Set default variables
        _perkInfo = self.mGetPerksDict(aLanguage=aLanguage)
        _perks = set()
        # Load perks
        for _perkId in _perkInfo:
            _perk = _perkInfo[_perkId]
            _perks.add(Perk(_perkId, _perk))
        return _perks

    def mUpdateBlacklistStatus(self) -> None:
        # Filter blacklisted perks
        for _perk in self.__perks:
            if _perk.id in self.__blacklist:
                _perk.mBlacklist()

    def mGetPerkIdByName(self, aPerkName: str) -> str:
        # Get perk id by name
        _result = next((_perk.id for _perk in self.__perks if _perk.title == aPerkName), None)
        if not _result:
            mLogError(f'Perk {aPerkName} not found')
            raise ValueError(f'Perk {aPerkName} not found')
        return _result

    def mGetPerkNameById(self, aPerkId: str) -> str:
        _result = next((_perk.title for _perk in self.__perks if _perk.id == aPerkId), None)
        if not _result:
            mLogError(f'Perk {aPerkId} not found')
            raise ValueError(f'Perk {aPerkId} not found')
        return _result

    def mGetPerkById(self, aPerkId: str) -> Perk:
        _result = next((_perk for _perk in self.__perks if _perk.id == aPerkId), None)
        if not _result:
            mLogError(f'Perk {aPerkId} not found')
            raise ValueError(f'Perk {aPerkId} not found')
        return _result

    def mGetBlackList(self) -> set:
        return self.__blacklist

    def mLoadBlackList(self) -> set:
        # Check if blacklist file exists
        if not os.path.exists(self.__blacklistPath):
            mWriteJsonFile(self.__blacklistPath, {})
        # Get user blacklist
        _blacklist = mParseJsonFile(self.__blacklistPath)
        _userBlacklist = _blacklist.get(self.__username, set())
        # Return user blacklist as a set
        mLogInfo(f'Blacklist loaded for user {self.__username}: {_userBlacklist}')
        return set(_userBlacklist)

    def mUpdateBlackListFile(self) -> None:
        # Save updated blacklist
        _blacklist = mParseJsonFile(self.__blacklistPath)
        _blacklist[self.__username] = list(self.__blacklist)
        mLogInfo(f'Current blacklist for user {self.__username}: {_blacklist}')
        mWriteJsonFile(self.__blacklistPath, _blacklist)
        mLogInfo(f'Blacklist updated for user {self.__username}')

    def mAddPerkToBlackList(self, aPerk: Perk) -> None:
        # Check if perk is already blacklisted
        if aPerk.mIsBlacklisted():
            mLogError(f'Perk {aPerk} is already blacklisted for user {self.__username}')
            return
        # Add perk to blacklist
        self.__blacklist.add(aPerk.id)
        aPerk.mBlacklist()
        mLogInfo(f'Perk {aPerk.title} added to blacklist for user {self.__username}')
        # Save updated blacklist
        self.mUpdateBlackListFile()

    def mRemovePerkFromBlackList(self, aPerk: Perk) -> None:
        # Check if perk is blacklisted
        if not aPerk.mIsBlacklisted():
            mLogError(f'Perk {aPerk} is not blacklisted for user {self.__username}')
            return
        # Remove perk from blacklist
        self.__blacklist.remove(aPerk.id)
        aPerk.mUnblacklist()
        mLogInfo(f'Perk {aPerk.title} removed from blacklist for user {self.__username}')
        # Save updated blacklist
        self.mUpdateBlackListFile()

    def mGetRandomPerk(self) -> Perk:
        # Get random perk
        _perk: Perk = random.choice(self.__perks)
        mLogInfo(f'Random perk {_perk.title} selected for user {self.__username}')
        return _perk

    def mGetRandomValidPerk(self) -> Perk:
        # Get random perk
        _perk: Perk = self.mGetRandomPerk()

        # Check if perk is blacklisted
        while not _perk.mIsValid():
            _perk.mUpdateUses()
            mLogError(f'Perk {self.mGetPerkNameById(_perk)} is blacklisted or repeated for user {self.__userid}. Getting another perk')
            _perk = self.mGetRandomPerk()

        # Get all the information of the perk
        _perk.mUpdateUses()
        mLogInfo(f'Valid perk {self.mGetPerkNameById(_perk)} selected for user {self.__userid}')
        return _perk

    def mGetRoll(self) -> list[Perk]:
        # Get random perks
        _roll = []
        for _ in range(self.BUILD_SIZE):
            _perk = self.mGetRandomValidPerk()
            _roll.append(_perk)
        # Update last roll
        self.mSetLastRoll(_roll)
        return _roll

    def mGetLastRoll(self) -> list[Perk]:
        return self.__lastRoll

    def mSetLastRoll(self, aRoll: list) -> None:
        self.last_roll = aRoll
        mLogInfo(f'Last roll set for user {self.__userid}. Roll: {aRoll}')

    def mGetWhitelistedPerkNames(self) -> list[str]:
        return [_perk.title for _perk in self.__perks if not _perk.mIsBlacklisted()]

    def mGetBlacklistedPerkNames(self) -> list[str]:
        return [_perk.title for _perk in self.__perks if _perk.mIsBlacklisted()]

    def mGetAllPerkNames(self) -> list[str]:
        return [_perk.title for _perk in self.__perks]
