# General imports
import os

# Specific imports
from discord import Interaction, Message

# Custom imports
from entities.workers.dbd.worker import DbdWorker
from entities.utils.files import mUpdatePerksJSON, mGetConfigDir, mGetDBDDataDir, mExtractCSVData, mCleanNonProjectIds, mGetFile, mCleanPerkImgFiles, mUpdateCSVBasedOnJSONFile
from entities.utils.rare import mBuildEnlistedMessage
from log.logger import mLogError, mLogInfo


class DbdHandler:

    __configDir = mGetConfigDir()
    __perksPath = os.path.join(__configDir, 'dbdperks.json')
    __imgDir = mGetFile("assets/dbd/imgs")
    __spriteSheet = os.path.join(__imgDir, 'surv-hd.png')
    __dataDir = mGetDBDDataDir()
    __csvTemplatePath = os.path.join(__dataDir, 'dbdperks_register_template.csv')
    __csvPath = os.path.join(__dataDir, 'dbdperkusage.csv')

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DbdHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.__workers = {}
        mLogInfo('Dbd handler initialized')
        # mUpdateCSVBasedOnJSONFile(self.__perksPath, self.__csvPath)
        # mUpdatePerksJSON(self.__perksPath) # Transform only once
        # mCleanNonProjectIds(self.__imgDir)
        # mUpdateDBDUsageCSVFile(self.__perksPath, self.__csvPath)
        # mUpdateDBDUsageCSVFile(self.__perksPath, self.__csvTemplatePath)

    # Creates a worker and optionally returns it
    def mCreateWorker(self, aCtx: Interaction) -> DbdWorker:
        # Check if worker already exists
        _userId = aCtx.user.id
        
        if _userId in self.__workers:
            mLogError(f'Worker for user {_userId} already exists')
            return self.__workers[_userId]

        # Create worker and return it
        _worker = DbdWorker(aCtx)
        self.__workers[_userId] = _worker
        mLogInfo(f'Current workers: {self.__workers}')
        return _worker

    # Stop a worker
    def mStopWorker(self, aUserId: str) -> None:
        # Check if worker exists
        if aUserId not in self.__workers:
            _errMsg = f'Worker for user {aUserId} does not exist'
            mLogError(_errMsg)
            raise ValueError(_errMsg)

        # Stop and remove worker
        _worker = self.mGetWorker(aUserId)
        _worker.mStop()

    # Stops and removes a worker
    def mRemoveWorker(self, aUserId: str, aForce: bool = False) -> None:
        # Check if worker exists
        try:
            _worker = self.mGetWorker(aUserId)
        except ValueError:
            mLogError(f'Worker for user {aUserId} does not exist')
            return

        # Check if worker is running
        if _worker.mIsRunning():
            mLogError(f'Worker for user {aUserId} is still running')
            
            # Force stop worker if needed
            if not aForce:
                mLogError(f'Worker for user {aUserId} not force stopped')
                return
            
            # Force stop worker
            mLogInfo(f'Force stopping worker for user {aUserId}')
            self.mStopWorker(aUserId)
    
        # Remove worker
        self.__workers.pop(aUserId)

    # Gets user id
    def mGetUserId(self, aCtx: Interaction) -> str:
        return aCtx.user.id

    # Returns a worker
    def mGetWorker(self, aUserId: str) -> DbdWorker:
        return self.__workers.get(aUserId, None)

    # Stores last message sent by the bot
    def mSetLastBuildId(self, aCtx: Interaction, aMessageId: int) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)
        
        # Try to store last message id
        try:
            _worker.mStart()
            _worker.mSetLastBuildId(aMessageId)
            _worker.mStop()
        except Exception as e:
            mLogError(f'Error setting build id: {e}')
            _worker.mStop()
            raise e

    # Gets last message sent by the bot
    def mGetLastBuildId(self, aCtx: Interaction) -> int:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Try to get last message id
        try:
            _worker.mStart()
            _msgId = _worker.mGetLastBuildId()
            _worker.mStop()
            return _msgId
        except Exception as e:
            mLogError(f'Error getting build id: {e}')
            _worker.mStop()
            raise e

    # Waits for five seconds and returns string
    def mGetRandomBuild(self, aCtx: Interaction) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Try to get random build
        try:
            _worker.mStart()
            _names, _collage = _worker.mGetRandomBuild(aCtx)
            _worker.mStop()
            # Return names and collage
            return _names, _collage
        except Exception as e:
            mLogError(f'Error getting random build: {e}')
            _worker.mStop()
            raise e

    # Adds perk to the user's blacklist
    def mAddPerkToBlacklist(self, aCtx: Interaction, aPerkId: str) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Add perk to blacklist
        try:
            _worker.mStart()
            _msg = _worker.mAddToBlackList(aPerkId)
            _worker.mStop()
            return _msg
        except Exception  as e:
            mLogError(f'Error adding perk to blacklist: {e}')
            _worker.mStop()
            raise e

    # Removes perk from the user's blacklist
    def mRemovePerkFromBlacklist(self, aCtx: Interaction, aPerkId: str) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Remove perk from blacklist
        try:
            _worker.mStart()
            _msg = _worker.mRemoveFromBlackList(aPerkId)
            _worker.mStop()
            return _msg
        except Exception as e:
            mLogError(f'Error removing perk from blacklist: {e}')
            _worker.mStop()

    # Replaces perk in the user's build
    def mReplacePerk(self, aCtx: Interaction, aPerkIndex: int) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Replace perk
        try:
            _worker.mStart()
            _perks, _collage = _worker.mReplacePerk(aCtx, aPerkIndex)
            _worker.mStop()
            return _perks, _collage
        except (ValueError, IndexError) as e:
            mLogError(f'Error replacing perk: {e}')
            _worker.mStop()
            raise e

    # Gets all valid perks
    def mGetWhitelistedPerkNames(self, aCtx: Interaction) -> dict:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _worker.mStart()
            _perks = _worker.mGetWhitelistedPerkNames()
            _worker.mStop()
            return _perks
        except Exception as e:
            mLogError(f'Error getting whitelisted perks: {e}')
            raise e

    # Gets all blacklisted perks
    def mGetBlacklistedPerkNames(self, aCtx: Interaction) -> list[str]:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _worker.mStart()
            _blacklistedPerks = _worker.mGetBlacklistedPerkNames()
            _worker.mStop()
            return _blacklistedPerks
        except Exception as e:
            mLogError(f'Error getting blacklisted perks: {e}')
            raise

    # Gets all perks
    def mGetAllPerkNames(self, aCtx: Interaction) -> dict:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get all perks
        try:
            _worker.mStart()
            _perks = _worker.mGetPerkNames()
            _worker.mStop()
            return _perks
        except Exception as e:
            mLogError(f'Error getting perks: {e}')
            raise e

    # Gets a perk's name by id
    def mGetPerkName(self, aCtx: Interaction, aPerkId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get perk name
        try:
            _worker.mStart()
            _perkName = _worker.mGetPerkName(aPerkId)
            _worker.mStop()
            return _perkName
        except Exception as e:
            mLogError(f'Error getting perk name: {e}')
            raise e

    # Gets help for a perk
    def mGetHelp(self, aCtx: Interaction, aId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get help by name
        try:
            _worker.mStart()
            _msg = _worker.mGetHelp(aId)
            _worker.mStop()
            return _msg
        except Exception as e:
            mLogError(f'Error getting help by name: {e}')
            raise e

    def mGetPerkIdByName(self, aCtx: Interaction, aPerkName: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get perk id
        try:
            _worker.mStart()
            _perkId = _worker.mGetPerkIdByName(aPerkName)
            _worker.mStop()
            return _perkId
        except Exception as e:
            mLogError(f'Error getting perk id from name: {e}')
            raise e

    def mGetPerkIdFromBuild(self, aCtx: Interaction, aPerkIndex: int) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get perk id
        try:
            _worker.mStart()
            _perkId = _worker.mGetPerkIdFromBuild(aPerkIndex)
            _worker.mStop()
            return _perkId
        except Exception as e:
            mLogError(f'Error getting perk id from build: {e}')
            raise e

    def mGetPerkImage(self, aCtx: Interaction, aPerkId: str) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get image
        try:
            _worker.mStart()
            _image = _worker.mGetPerkImage(aPerkId)
            _worker.mStop()
            return _image
        except Exception as e:
            mLogError(f'Error getting perk image: {e}')
            raise e

    def mRegisterWin(self, aCtx: Interaction) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Register win
        try:
            _worker.mStart()
            _worker.mRegisterResult(True)
            _worker.mStop()
        except Exception as e:
            mLogError(f'Error registering win: {e}')
            raise e

    def mRegisterLoss(self, aCtx: Interaction) -> None:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Register win
        try:
            _worker.mStart()
            _worker.mRegisterResult(False)
            _worker.mStop()
        except Exception as e:
            mLogError(f'Error registering loss: {e}')
            raise e

    def mSetCustomBuild(self, aCtx: Interaction, aPerkIds: list[str]) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Set custom build
        try:
            _worker.mStart()
            _names, _collage = _worker.mSetCustomBuild(aCtx, aPerkIds)
            _worker.mStop()
            return _names, _collage
        except Exception as e:
            mLogError(f'Error setting custom build: {e}')
            raise e

    def mGetUsageGraph(self, aCtx: Interaction, aUser: bool = False) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Get usage graph
        try:
            _worker.mStart()
            _userId = aCtx.user.id if aUser else None
            _graph = _worker.mGetUsageGraph(aUserId=_userId)
            _worker.mStop()
            return _graph
        except Exception as e:
            mLogError(f'Error getting usage graph: {e}')
            raise e

    def mRandomizeCSVData(self, aCtx: Interaction) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Randomize CSV data
        try:
            _worker.mStart()
            if aCtx.user.id != 612432506813284373:
                raise ValueError('You are not allowed to randomize CSV data.')
            _msg = _worker.mRandomizeCSVData()
            _worker.mStop()
            return _msg
        except Exception as e:
            mLogError(f'Error randomizing CSV data: {e}')
            raise e

    def mResetCSVData(self, aCtx: Interaction) -> str:
        # Get worker
        _worker = self.mCreateWorker(aCtx)

        # Reset CSV data
        try:
            _worker.mStart()
            if aCtx.user.id != 612432506813284373:
                raise ValueError('You are not allowed to reset CSV data.')
            _msg = _worker.mResetCSVData()
            _worker.mStop()
            return _msg
        except Exception as e:
            mLogError(f'Error resetting CSV data: {e}')
            raise e