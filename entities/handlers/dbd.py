# General imports
import threading
from typing import Any

# Specific imports
from discord import Interaction, File
# Custom imports
from entities.workers.dbd.worker import DbdWorker
from log.logger import mLogError, mLogInfo

class DbdHandler:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DbdHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.__workers = {}
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
    def mSetLastBuildId(self, aCtx: Interaction, aMessageId: int) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)
        
        # Try to store last message id
        try:
            _worker.mSetLastBuildId(aMessageId)
        except Exception as e:
            mLogError(f'Error setting build id: {e}')
            raise e

    # Gets last message sent by the bot
    def mGetLastBuildId(self, aCtx: Interaction) -> int:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Try to get last message id
        try:
            _msgId = _worker.mGetLastBuildId()
            return _msgId
        except Exception as e:
            mLogError(f'Error getting build id: {e}')
            raise e

    # Waits for five seconds and returns string
    def mGetRandomBuild(self, aCtx: Interaction) -> tuple:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Try to get random build
        try:
            _names, _collage = _worker.mGetRandomBuild(aCtx)
            return _names, _collage
        except Exception as e:
            mLogError(f'Error getting random build: {e}')
            raise e

    # Adds perk to the user's blacklist
    def mAddPerkToBlacklist(self, aCtx: Interaction, aPerkId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Add perk to blacklist
        try:
            _msg = _worker.mAddToBlackList(aPerkId)
            return _msg
        except Exception  as e:
            mLogError(f'Error adding perk to blacklist: {e}')
            raise e

    # Removes perk from the user's blacklist
    def mRemovePerkFromBlacklist(self, aCtx: Interaction, aPerkId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Remove perk from blacklist
        try:
            _msg = _worker.mRemoveFromBlackList(aPerkId)
            return _msg
        except Exception as e:
            mLogError(f'Error removing perk from blacklist: {e}')

    # Replaces perk in the user's build
    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> tuple[list[str], File]:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Replace perk
        try:
            _perks, _collage = _worker.mReplacePerk(aCtx, aPerkIndex)
            return _perks, _collage
        except (ValueError, IndexError) as e:
            mLogError(f'Error replacing perk: {e}')
            raise e

    # Gets all valid perks
    def mGetWhitelistedPerkNames(self, aCtx: Interaction) -> list:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _perks = _worker.mGetWhitelistedPerkNames()
            return _perks
        except Exception as e:
            mLogError(f'Error getting whitelisted perks: {e}')
            raise e

    # Gets all blacklisted perks
    def mGetBlacklistedPerkNames(self, aCtx: Interaction) -> set:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _blacklistedPerks = _worker.mGetBlacklistedPerkNames()
            return _blacklistedPerks
        except Exception as e:
            mLogError(f'Error getting blacklisted perks: {e}')
            raise

    # Gets all perks
    def mGetAllPerkNames(self, aCtx: Interaction) -> list:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _perks = _worker.mGetPerkNames()
            return _perks
        except Exception as e:
            mLogError(f'Error getting perks: {e}')
            raise e

    # Gets help for a perk
    def mGetHelp(self, aCtx: Interaction, aId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get help by name
        try:
            _msg = _worker.mGetHelp(aId)
            return _msg
        except Exception as e:
            mLogError(f'Error getting help by name: {e}')
            raise e

    def mGetPerkIdFromBuild(self, aCtx: Interaction, aPerkIndex: int) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get perk id
        try:
            _perkId = _worker.mGetPerkFromBuild(aPerkIndex)
            return _perkId
        except Exception as e:
            mLogError(f'Error getting perk id from build: {e}')
            raise e

    def mGetPerkImage(self, aCtx: Interaction, aPerkId: str) -> File:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get image
        try:
            _image = _worker.mGetPerkImage(aPerkId)
            return _image
        except Exception as e:
            mLogError(f'Error getting perk image: {e}')
            raise e

    def mRegisterWin(self, aCtx: Interaction, aPerkIds: list[str]) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Register win
        try:
            _worker.mRegisterResult(True, aPerkIds)
        except Exception as e:
            mLogError(f"Error registering win: {e}")
            raise e

    def mRegisterLoss(self, aCtx: Interaction, aPerkIds: list[str]) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Register loss
        try:
            _worker.mRegisterResult(False, aPerkIds)
        except Exception as e:
            mLogError(f"Error registering loss: {e}")
            raise e

    def mSetCustomBuild(self, aCtx: Interaction, aPerkIds: list[str]) -> tuple[Any, Any]:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Set custom build
        try:
            _names, _collage = _worker.mSetCustomBuild(aCtx, aPerkIds)
            return _names, _collage
        except Exception as e:
            mLogError(f'Error setting custom build: {e}')
            raise e

    def mGetUsageGraph(self, aCtx: Interaction, aUser: int = None) -> File:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get usage graph
        try:
            _userId = aCtx.user.id if aUser else None
            _graph = _worker.mGetUsageGraph(aUser=aUser)
            return _graph
        except Exception as e:
            mLogError(f'Error getting usage graph: {e}')
            raise e

    def mUpdateBlacklistToDB(self) -> None:
        for _worker in self.__workers.values():
            try:
                _worker.mUpdateUserBlackList(aForce=True)
                _worker.mKillSQLRetriever()
            except Exception as e:
                mLogError(f'Error updating blacklist: {e}')
                raise e
