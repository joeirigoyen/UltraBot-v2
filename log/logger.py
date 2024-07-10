# Generic imports
import logging
import sys

# Configure the logger
_logger = logging.getLogger("UltraBot")
_logger.setLevel(logging.INFO)

# Configure the handlers
_handlers = {}

# Create formatters
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(filename)s @ %(funcName)s:%(lineno)d | %(message)s')

# Create a handler for the logger
def mCreateHandler(log_file: str = None, log_level: int = logging.INFO):
    """
    Create a handler for the logger. Doesn't add it to the logger.
    
    Args:
        log_file (str, optional): The file to log to. Defaults to None.
        log_level (int, optional): The level to log at. Defaults to logging.INFO.

    Returns:
        _type_: _description_
    """
    if log_file:
        handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    return handler

# Configure specific loggers
def mSetHandlerToLogger(name: str, log_file: str, log_level: int) -> None:
    """
    Configure a handler for a specific logger.

    Args:
        name (str): The name of the logger.
        log_file (str): The file to log to.
        log_level (int): The level of the logger.
    """
    # Create the handler
    _handler = mCreateHandler(log_file, log_level)
    # Configure the logger
    _handler.setLevel(log_level)
    _handler.setFormatter(formatter)
    # Add the handler to the logger
    _handlers[name] = _handler
    _logger.addHandler(_handler)

# Initialize hadlers
mSetHandlerToLogger('info', 'log/info.log', logging.INFO)
mSetHandlerToLogger('error', 'log/error.log', logging.ERROR)
mSetHandlerToLogger('trace', 'log/trace.log', logging.DEBUG)
mSetHandlerToLogger('discord', 'log/discord.log', logging.DEBUG)

# Public access methods
def mLogInfo(message):
    _logger.info(message, stacklevel=2)

def mLogDebug(message):
    _logger.debug(message, stacklevel=2)

def mLogError(message):
    _logger.error(message, stacklevel=2)

def mGetHandler(name):
    return _handlers.get(name)
