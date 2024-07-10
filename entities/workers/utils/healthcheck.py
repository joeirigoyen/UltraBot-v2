# General imports
from datetime import datetime, timedelta
import time
import threading

# Specific imports
from dataclasses import dataclass
from enum import Enum

# Custom imports
from entities.utils.files import  mParseJsonFile, mGetFile, mCleanupDbdGenImgsDir
from log.logger import mLogInfo, mLogError


class TaskType(Enum):
    CLEAN_DBD_GEN_IMGS = "cleanup_dbd_generated_images"

@dataclass
class TaskInfo:
    name: str
    interval: timedelta
    last_run: datetime
    next_run: datetime

class HealthWorker:

    # Set paths
    __invervalsDir = 'config/hctasks.json'
    __intervalsFile = mGetFile(__invervalsDir)

    def __init__(self):
        # Set stop event
        self.__stopEvent = threading.Event()
        # Get intervals dictionary
        self.__intervals = mParseJsonFile(self.__intervalsFile)
        self.__tasks: set[TaskInfo] = self.mLoadTasks()
        # Get last run of each task every checkInterval
        self.__checkInterval = 60 # Every minute

    def mIsTaskNameValid(self, aTaskName: str) -> bool:
        return aTaskName in TaskType.__members__

    def mLoadTasks(self) -> set:
        _tasks = []
        for _taskName, _taskInterval in self.__intervals.items():
            # Check if task name is valid
            if not self.mIsTaskNameValid(_taskName):
                mLogError(f'Task {_taskName} not found')
                continue
            # Create task
            _taskType = TaskType(_taskName)
            _task = TaskInfo(_taskType, timedelta(minutes=_taskInterval), datetime.now(), datetime.now() + timedelta(minutes=_taskInterval))
            _tasks.append(_task)
        return _tasks

    def mUpdateTaskRuntime(self, aTask: TaskInfo) -> None:
        aTask.last_run = datetime.now()
        aTask.next_run = aTask.last_run + aTask.interval
        return aTask

    def mRunTask(self, task: TaskInfo) -> None:
        if task.name == TaskType.CLEAN_DBD_GEN_IMGS:
            mCleanupDbdGenImgsDir()
        else:
            mLogError(f'Task {task.name} not found')

    def mRun(self) -> None:
        while not self.__stopEvent.is_set():
            _now = datetime.now()
            mLogInfo(f'Checking if any task needs to be run.')
            for _task in self.__tasks:
                if _now >= _task.next_run:
                    mLogInfo(f'Task {_task.name} needs to be run.')
                    threading.Thread(target=self.mRunTask, args=(_task,)).start()
                    self.mUpdateTaskRuntime(_task)
                    mLogInfo(f'Task {_task.name} runtime updated to {_task.next_run}.')
            mLogInfo(f'All tasks checked. Sleeping for {self.__checkInterval} seconds.')
            time.sleep(self.__checkInterval)

    def start(self):
        mLogInfo('Starting healthcheck worker')
        self.thread = threading.Thread(target=self.mRun)
        self.thread.start()

    def stop(self):
        mLogInfo('Stopping healthcheck worker')
        self.__stopEvent.set()
        self.thread.join()