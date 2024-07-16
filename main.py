# Specific imports
from dotenv import load_dotenv
from os import getenv, path, mkdir
from threading import Thread

# Custom imports
from entities.bot import mRun
from entities.workers.utils.healthcheck import HealthWorker
from entities.utils.files import mDownloadFromGDrive, mExtractZip, mGetFile, mGetDBDConfig
from log.logger import mLogInfo

class Runner:
    """
    This class is the main class of the bot. It initializes the bot and runs it.
    """
    
    def __init__(self):
        # Load the environment variables
        load_dotenv()
        mLogInfo('Environment variables loaded')    
    
    def mRunBot(self):
        """
        This method runs the bot.
        """

        # Download additional assets
        # DBD Perk Images
        _perkImgUrl = mGetDBDConfig().get('PERKS_IMG_URL')
        _perkDir = mGetFile('assets/dbd/imgs/perks')
        _perkZipName = path.join(_perkDir, 'perkimgs.zip')
        if not path.exists(_perkDir):
            mLogInfo(f'Creating directory for perk images: {_perkDir}')
            mkdir(_perkDir)
            mDownloadFromGDrive(_perkImgUrl, _perkZipName)
            mExtractZip(_perkZipName, _perkDir, aRemoveWhenDone=True)
            mLogInfo('Perk images downloaded and extracted')

        # Run healtcheck worker
        _hcWorker = HealthWorker()
        _hcThread = Thread(target=_hcWorker.mRun, daemon=True)
        _hcThread.start()

        # Run the bot
        try:
            _token = getenv('DISCORD_TOKEN')
            mLogInfo(f'Calling run method of bot with token: {_token}')
            mRun(aToken=_token)
        except KeyboardInterrupt:
            mLogInfo('Bot stopped by user')
            exit(0)


if __name__ == '__main__':
    runner = Runner()
    runner.mRunBot()
