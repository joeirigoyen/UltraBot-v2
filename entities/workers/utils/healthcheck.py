# General imports
from datetime import datetime, timedelta
import time
import threading

# Specific imports
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from threading import Thread

# Custom imports
from entities.utils.files import  mParseJsonFile, mGetFile, mCleanupDbdGenImgsDir, mWriteJsonFile
from log.logger import mLogInfo, mLogError

class TaskNames(Enum):
    CLEANUP_DBD_GENERATED_IMAGES = 'cleanup_dbd_generated_imgs'

@dataclass
class TaskInfo:
    name: str
    interval: timedelta
    last_run: datetime
    next_run: datetime


def mRunTask(task: TaskInfo) -> None:
    match task.name:
        case TaskNames.CLEANUP_DBD_GENERATED_IMAGES.value:
            mLogInfo(f'Running task {task.name}')
            mCleanupDbdGenImgsDir(aExcludeFiles=['.gitignore'])
            mLogInfo(f'Task {task.name} finished')
        case _:
            mLogError(f'Task {task.name} not found')


class HealthWorker:

    # Set paths
    __invervalsPath = 'config/hctasks.json'
    __intervalsFile = mGetFile(__invervalsPath)

    def __init__(self):
        # Set stop event
        self.__stopEvent = threading.Event()
        # Get intervals dictionary
        self.__intervals: dict[str, dict] = mParseJsonFile(self.__intervalsFile)
        self.__tasks: list[TaskInfo] = self.mLoadTasks()
        # Get last run of each task every checkInterval
        self.__checkInterval = 1 # Every minute
        self.__daemon: Thread | None = None

    def mGetTasknameSet(self) -> set:
        return set(self.__intervals.keys())

    @staticmethod
    def mCalculateNextRun(aLastRun: datetime, aInterval: timedelta | int) -> datetime:
        # Convert interval to timedelta if int
        if isinstance(aInterval, int):
            aInterval = timedelta(minutes=aInterval)
        # If next run is in the past, set next run to now + interval
        if aLastRun + aInterval < datetime.now():
            _nextRun = datetime.now() + aInterval
            return _nextRun
        return aLastRun + aInterval

    @staticmethod
    def mDateTimeToStr(aDateTime: datetime) -> str:
        return aDateTime.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def mStrToDateTime(aStr: str) -> datetime:
        return datetime.strptime(aStr, '%Y-%m-%d %H:%M:%S')

    def mLoadTasks(self) -> list[TaskInfo]:
        _tasks = []
        for _taskName, _taskInfo in self.__intervals.items():
            # Convert last run to datetime and string
            _lastRun = _taskInfo.get('last_run', datetime.now())
            _lastRunStr = _lastRun if isinstance(_lastRun, str) else self.mDateTimeToStr(_lastRun)
            _lastRunDt = self.mStrToDateTime(_lastRunStr)
            # Update last run if different
            if _lastRunStr != _taskInfo.get('last_run'):
                _taskInfo['last_run'] = _lastRunStr
            # Calculate next run
            _interval = _taskInfo.get('interval', timedelta(minutes=60))
            _nextRun = self.mCalculateNextRun(_lastRunDt, _interval)
            _task = TaskInfo(_taskName, _interval, _lastRunDt, _nextRun)
            _tasks.append(_task)
        # Rewrite to json file
        mWriteJsonFile(self.__intervalsFile, self.__intervals)
        return _tasks

    def mUpdateTaskRuntime(self, aTask: TaskInfo) -> TaskInfo:
        # Update internally
        aTask.last_run = datetime.now()
        aTask.next_run = aTask.last_run + timedelta(minutes=aTask.interval)
        # Update in file
        _taskInfo = self.__intervals.get(aTask.name)
        _taskInfo['last_run'] = self.mDateTimeToStr(aTask.last_run)
        mWriteJsonFile(self.__intervalsFile, self.__intervals)
        return aTask

    def mRun(self) -> None:
        while not self.__stopEvent.is_set():
            _now = datetime.now()
            mLogInfo(f'Checking if any task needs to be run.')
            _runningTasks = list()
            for _task in self.__tasks:
                if _now >= _task.next_run:
                    mLogInfo(f'Task {_task.name} needs to be run.')
                    _thread = threading.Thread(target=mRunTask, args=(_task,))
                    _runningTasks.append(_thread)
                    _thread.start()
                    self.mUpdateTaskRuntime(_task)
            for _thread in _runningTasks:
                _thread.join()
                mLogInfo(f'Task {_thread.name} runtime updated.')
            mLogInfo(f'All tasks checked. Sleeping for {self.__checkInterval} minutes.')
            time.sleep(self.__checkInterval * 60)

    def start(self):
        mLogInfo('Starting healthcheck worker')
        self.__daemon = threading.Thread(target=self.mRun)
        self.__daemon.start()
        self.__daemon.daemon = True

    def stop(self):
        mLogInfo('Stopping healthcheck worker')
        self.__stopEvent.set()
        self.__daemon.join(timeout=300)
        if self.__daemon.is_alive():
            mLogError('Healthcheck worker could not be stopped gracefully')