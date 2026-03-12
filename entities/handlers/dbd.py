# General imports
from typing import Any
from cachetools import TTLCache
from functools import wraps

# Specific imports
from discord import Interaction, File
# Custom imports
from entities.workers.dbd.worker import DbdWorker
from log.logger import mLogError, mLogInfo

def mHandleDbdErrors(error_msg: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                mLogError(f'{error_msg}: {e}')
                raise e
        return wrapper
    return decorator

class DbdHandler:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DbdHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.__workers = TTLCache(maxsize=500, ttl=3600)
        mLogInfo('Dbd handler initialized')

    # Creates a worker and optionally returns it
    def mCreateWorker(self, aCtx: Interaction) -> DbdWorker:
        # Check if worker already exists
        _userId = aCtx.user.id
        
        if _userId in self.__workers:
            mLogInfo(f'Found worker for user {_userId}')
            return self.__workers[_userId]

        # Create worker and return it
        _worker = DbdWorker(aCtx)
        self.__workers[_userId] = _worker
        mLogInfo(f'Created worker for user {_userId}')
        mLogInfo(f'Current workers: {self.__workers}')
        return _worker

    # Gets user id
    @staticmethod
    def mGetUserId(aCtx: Interaction) -> int:
        return aCtx.user.id

    # Returns a worker
    def mGetWorker(self, aUserId: str) -> DbdWorker | None:
        return self.__workers.get(aUserId, None)

    # Stores last message sent by the bot
    @mHandleDbdErrors('Error setting build id')
    def mSetLastBuildId(self, aCtx: Interaction, aMessageId: int) -> None:
        self.mCreateWorker(aCtx).mSetLastBuildId(aMessageId)

    # Gets last message sent by the bot
    @mHandleDbdErrors('Error getting build id')
    def mGetLastBuildId(self, aCtx: Interaction) -> int:
        return self.mCreateWorker(aCtx).mGetLastBuildId()

    # Waits for five seconds and returns string
    @mHandleDbdErrors('Error getting random build')
    def mGetRandomBuild(self, aCtx: Interaction) -> tuple:
        return self.mCreateWorker(aCtx).mGetRandomBuild(aCtx)

    # Gets random perk suggestion given a type of perk
    @mHandleDbdErrors('Error getting suggestion')
    def mGetSuggestion(self, aCtx: Interaction, aPerkType: str) -> tuple:
        return self.mCreateWorker(aCtx).mGetSuggestion(aCtx, aPerkType)

    # Adds perk to the user's blacklist
    @mHandleDbdErrors('Error adding perk to blacklist')
    def mAddPerkToBlacklist(self, aCtx: Interaction, aPerkId: str) -> str:
        return self.mCreateWorker(aCtx).mAddToBlackList(aPerkId)

    # Removes perk from the user's blacklist
    @mHandleDbdErrors('Error removing perk from blacklist')
    def mRemovePerkFromBlacklist(self, aCtx: Interaction, aPerkId: str) -> str:
        return self.mCreateWorker(aCtx).mRemoveFromBlackList(aPerkId)

    # Replaces perk in the user's build
    @mHandleDbdErrors('Error replacing perk')
    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> tuple[list[str], File]:
        return self.mCreateWorker(aCtx).mReplacePerk(aCtx, aPerkIndex)

    # Replaces various perks in the user's build
    @mHandleDbdErrors('Error replacing perks')
    def mReplacePerks(self, aCtx: Interaction, aPerkIndices: list[int]) -> tuple[list[str], File]:
        return self.mCreateWorker(aCtx).mReplacePerks(aCtx, aPerkIndices)

    # Gets all valid perks
    @mHandleDbdErrors('Error getting whitelisted perks')
    def mGetWhitelistedPerkNames(self, aCtx: Interaction) -> list:
        return self.mCreateWorker(aCtx).mGetWhitelistedPerkNames()

    # Gets all blacklisted perks
    @mHandleDbdErrors('Error getting blacklisted perks')
    def mGetBlacklistedPerkNames(self, aCtx: Interaction) -> set:
        return self.mCreateWorker(aCtx).mGetBlacklistedPerkNames()

    # Gets all perks
    @mHandleDbdErrors('Error getting perks')
    def mGetAllPerkNames(self, aCtx: Interaction) -> list:
        return self.mCreateWorker(aCtx).mGetPerkNames()

    # Gets help for a perk
    @mHandleDbdErrors('Error getting help by name')
    def mGetHelp(self, aCtx: Interaction, aId: str) -> dict:
        return self.mCreateWorker(aCtx).mGetHelp(aId)

    @mHandleDbdErrors('Error getting perk id from build')
    def mGetPerkIdFromBuild(self, aCtx: Interaction, aPerkIndex: int) -> str:
        return self.mCreateWorker(aCtx).mGetPerkFromBuild(aPerkIndex)

    @mHandleDbdErrors('Error getting perk image')
    def mGetPerkImage(self, aCtx: Interaction, aPerkId: str) -> File:
        return self.mCreateWorker(aCtx).mGetPerkImage(aPerkId)

    @mHandleDbdErrors('Error registering win')
    def mRegisterWin(self, aCtx: Interaction, aPerkIds: list[str]) -> None:
        self.mCreateWorker(aCtx).mRegisterResult(True, aPerkIds)

    @mHandleDbdErrors('Error registering loss')
    def mRegisterLoss(self, aCtx: Interaction, aPerkIds: list[str]) -> None:
        self.mCreateWorker(aCtx).mRegisterResult(False, aPerkIds)

    @mHandleDbdErrors('Error setting custom build')
    def mSetCustomBuild(self, aCtx: Interaction, aPerkIds: list[str]) -> tuple[Any, Any]:
        return self.mCreateWorker(aCtx).mSetCustomBuild(aCtx, aPerkIds)

    @mHandleDbdErrors('Error getting usage stats')
    def mGetUsageStats(self, aCtx: Interaction, aUser: str = None) -> dict:
        return self.mCreateWorker(aCtx).mGetUsageStats(aUser=aUser)

    def mUpdateBlacklistToDB(self) -> None:
        for _worker in self.__workers.values():
            try:
                _worker.mUpdateUserBlackList(aForce=True)
                _worker.mKillSQLRetriever()
            except Exception as e:
                mLogError(f'Error updating blacklist: {e}')
                raise e
