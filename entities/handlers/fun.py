# General imports
from typing import Any

# Specific imports
from discord import Interaction, File
# Custom imports
from entities.workers.fun.worker import FunWorker
from log.logger import mLogError, mLogInfo

class FunHandler:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(FunHandler, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.__workers = {}
        mLogInfo('Fun handler initialized')

    # Creates a worker and optionally returns it
    def mCreateWorker(self, aCtx: Interaction) -> FunWorker:
        # Check if worker already exists
        _userId = aCtx.user.id
        
        if _userId in self.__workers:
            mLogInfo(f'Found worker for user {_userId}')
            return self.__workers[_userId]

        # Create worker and return it
        _worker = FunWorker(aCtx)
        self.__workers[_userId] = _worker
        mLogInfo(f'Created worker for user {_userId}')
        mLogInfo(f'Current workers: {self.__workers}')
        return _worker