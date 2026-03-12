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


class FunWorker:

    __assetsDir = mGetAssetsDir()
    __dbdAssetsDir = os.path.join(__assetsDir, 'dbd')
    __dbdGenImagesDir = mGetConfigProperty("GENERATED_IMG_DIR")
    
    def __init__(self, aCtx: Interaction):
        # Set owner
        self.__userId = str(aCtx.user.id)
        self.__userName = aCtx.user.name

    @property
    def userId(self):
        return self.__userId
    
    @property
    def userName(self):
        return self.__userName