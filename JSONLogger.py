import os
import imp
import sys
import logging
from logging.handlers import WatchedFileHandler
from driftwood.formatters import JSONFormatter
from stat import ST_DEV, ST_INO, ST_MTIME, ST_SIZE
import multiprocessing
from functools import reduce


class Color(object):
    colors = {
        'black': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'cyan': 36,
        'white': 37,
        'bgred': 41,
        'bggrey': 100
    }
    prefix = '\033['
    suffix = '\033[0m'

    def colored(self, text, color=None):
        if color not in self.colors:
            color = 'white'
        clr = self.colors[color]
        return (self.prefix + '{0}m{1}' + self.suffix).format(clr, text)


colored = Color().colored


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        asctime = self.formatTime(record, self.datefmt)
        mapping = {
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bgred',
            'DEBUG': 'bggrey',
            'SUCCESS': 'green'
        }
        clr = mapping.get(record.levelname, 'white')
        return '[{0}] [pid:{1}] [{2}] [{3}] : {4}'.format(colored(asctime, 'blue'),
                                                          record.process,
                                                          record.funcName,
                                                          colored(record.levelname, clr),
                                                          colored(message, clr))


class JSONFileHandler(WatchedFileHandler):
    def _open(self):
        open(self.baseFilename, 'a').close()
        return open(self.baseFilename, self.mode, encoding=self.encoding)

    def emit(self, record):
        """
        Emit a record.

        First check if the underlying file has changed, and if it
        has, close the old stream and reopen the file to get the
        current stream.
        """
        # self.terminator = ']'
        self.new = False

        try:
            # stat the file by path, checking for existence
            sres = os.stat(self.baseFilename)
        except FileNotFoundError:
            sres = None

        # compare file system stat with that of our stream file handle
        if not sres or sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino:
            if self.stream is not None:
                # we have an open file handle, clean it up
                self.stream.flush()
                self.stream.close()
                self.stream = None
                self.stream = self._open()
                self._statstream()
            self.new = True
        elif sres[ST_SIZE] == 0:
            self.new = True

        self.log2file(record)

    def log2file(self, record):
        if self.stream is None:
            self.stream = self._open()
        try:
            if not self.new:
                self.stream.seek(0, os.SEEK_END)
                self.stream.seek(self.stream.tell() - 1)
                self.stream.write(',')
                msg = self.format(record)
                self.stream.write(msg)
                self.stream.write(']')
            else:
                self.stream.write('[')
                self.stream.seek(0, os.SEEK_END)
                msg = self.format(record)
                self.stream.write(msg)
                self.stream.write(']')
            self.flush()
        except Exception as err:
            print(str(err))

            
class CustomFilter(logging.Filter):
    def __init__(self, **kwargs):
        super().__init__()
        self._kwargs = deepcopy(kwargs)

    def filter(self, record):
        list(map(lambda x: setattr(record, x, self._kwargs[x]), self._kwargs))
        return True

    
class Logger():
    def __init__(self, *filename):
        # imp.reload(logging)
        self.print = logging.getLogger(reduce(lambda x,y: x+y, filename))
        self.print.propagate = False
        self.print.addFilter(CustomFilter(**kwargs))
        
        self.createDir(filename)

        logging.SUCCESS = 1
        logging.addLevelName(logging.SUCCESS, 'SUCCESS')
        setattr(self.print, 'success', lambda message, *args, **kws: {self.createDir(),
                                                                      self.print._log(logging.SUCCESS, message, args,
                                                                                      **kws)})
        self.print.setLevel(logging.SUCCESS)

        if not self.print.handlers:
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(ColoredFormatter())
            self.print.addHandler(streamHandler)
            fileFormatter = JSONFormatter(
                regular_attrs=["message", "levelname", "pathname", "filename", "module", "funcName", "asctime",
                               "lineno", "created", "process", "msecs"])
            # fileFormatter = logging.Formatter( '{ "time":"%(asctime)s", "pid":"%(process)s", "module":"%(funcName)s", "levelname":"%(levelname)s", "message":"%(message)s" }' )
            for file in filename:
                fileHandler = JSONFileHandler(file, mode='r+')
                fileHandler.setFormatter(fileFormatter)
                self.print.addHandler(fileHandler)

    def createDir(self, filename=()):
        for fl in filename:
            dirname = os.path.dirname(fl)
            if dirname != '':
                os.makedirs(dirname, exist_ok=True)
        for handler in self.print.handlers:
            if type(handler) == logging.FileHandler:
                dirname = os.path.dirname(handler.baseFilename)
                if dirname != '':
                    os.makedirs(dirname, exist_ok=True)


class LoggerManager:
    def __init__(self):
        self.queue = multiprocessing.Manager().Queue()
        self.log_files_dict = dict()
        self.print = self
        startQueueManager(self)
        # self.print = self

    def info(self, logfile, log_msg, **kwargs):
        self.queue.put(
            (logfile, sys._getframe().f_code.co_name, log_msg, kwargs))

    def error(self, logfile, log_msg, **kwargs):
        self.queue.put(
            (logfile, sys._getframe().f_code.co_name, log_msg, kwargs))

    def warning(self, logfile, log_msg, **kwargs):
        self.queue.put(
            (logfile, sys._getframe().f_code.co_name, log_msg, kwargs))

    def success(self, logfile, log_msg, **kwargs):
        self.queue.put(
            (logfile, sys._getframe().f_code.co_name, log_msg, kwargs))

    def debug(self, logfile, log_msg, **kwargs):
        self.queue.put(
            (logfile, sys._getframe().f_code.co_name, log_msg, kwargs))

    def log_print(self, file, log_level, log_msg, **kwargs):
        file = tuple(file)
        log = Logger(file, **kwargs)
        try:
            getattr(log.print, log_level)(log_msg)
            list(map(log.print.removeHandler, log.print.handlers))
        except Exception as err:
            print(str(err))

#     def lprint(self, logfile, loglevel, logmsg):
#         if type(logfile) == list:
#             list(map(lambda file: self.lp(file, loglevel, logmsg), logfile))
#         else:
#             file = logfile
#             self.lp(file, loglevel, logmsg)

#     def lp(self, file, loglevel, logmsg):
#         if file not in self.log_files_dict:
#             self.log_files_dict[file] = Logger(file)
#         try:
#             getattr(self.log_files_dict[file].print, loglevel)(logmsg)
#         except Exception as err:
#             print(str(err))


def startQueueManager(log):
    queueManager = multiprocessing.Process(target=QueueManager, args=(log,))
    queueManager.daemon = True
    queueManager.start()


def QueueManager(log):
    while True:
        try:
            log_file, log_level, log_msg, kwargs = log.queue.get(
                block=True, timeout=2)
            log.queue.task_done()
            log.log_print(log_file, log_level, log_msg, **kwargs)
#             if not log.queue.empty():
#                 logfile, loglevel, logmsg = log.queue.get_nowait()
#                 log.lprint(logfile, loglevel, logmsg)
        except Exception as err:
            # print( str(err) )
            pass

    
class ModuleLogger:
    def __init__(self, logger_manager, logfiles=[], **kwargs):
        self.log = logger_manager
        self.files = logfiles
        self.print = self
        self.append2formatter = kwargs if kwargs else {}

    def add_fields2formater(self, kwargs):
        self.append2formatter = kwargs

    def update_files(self, logfiles):
        self.files = logfiles

    def getLoggerMannager(self):
        return self.log

    def update_formatter(self, call_func):
        self.append2formatter['func_Name'] = call_func.f_code.co_name
        self.append2formatter['line_no'] = call_func.f_lineno
        self.append2formatter['call_module'] = call_func.f_globals['__name__']
        self.append2formatter['call_module'] = self.append2formatter[
            'call_module'].split('.')[-1]
        self.append2formatter['path_name'] = call_func.f_globals['__file__']

    def info(self, log_msg):
        self.update_formatter(sys._getframe().f_back)
        self.log.info(self.files, log_msg, **self.append2formatter)

    def error(self, log_msg):
        self.update_formatter(sys._getframe().f_back)
        self.log.error(self.files, log_msg, **self.append2formatter)

    def warning(self, log_msg):
        self.update_formatter(sys._getframe().f_back)
        self.log.warning(self.files, log_msg, **self.append2formatter)

    def success(self, log_msg):
        self.update_formatter(sys._getframe().f_back)
        self.log.success(self.files, log_msg, **self.append2formatter)

    def debug(self, log_msg):
        self.update_formatter(sys._getframe().f_back)
        self.log.debug(self.files, log_msg, **self.append2formatter)
