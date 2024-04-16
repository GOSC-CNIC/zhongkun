import os
import re
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from django.conf import settings
from .utils import DateUtils


def get_log_folder(path):
    path = os.path.join(settings.LOGGING_FILES_DIR, *Path(path).parts[-2:])
    return path.split(".")[0]


def split_filename(filename):
    file_path = filename.split('default.log.')
    return ''.join(file_path)


class CustomRotatingFileHandler(TimedRotatingFileHandler):
    def getFilesToDelete(self):
        dir_name, _ = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        for filename in file_names:
            if self.extMatch.match(filename):
                result.append(os.path.join(dir_name, filename))
        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[:len(result) - self.backupCount]
        return result


def setup_logger(log_name, file_name):
    file_name = get_log_folder(file_name)
    logger = logging.getLogger(log_name)
    logger_folder_path = Path(file_name)
    logger_folder_path.mkdir(parents=True, exist_ok=True)
    log_file_path = logger_folder_path / 'default.log'
    logger_handler = CustomRotatingFileHandler(filename=log_file_path, when='MIDNIGHT', interval=1, backupCount=10,
                                               encoding='utf-8')
    logger_handler.namer = split_filename
    logger_handler.suffix = f"{logger_handler.suffix}.log"
    logger_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}(.log)$", re.ASCII)
    logger_formatter = logging.Formatter(
        "[%(asctime)s] [%(process)d] [%(levelname)s] - %(module)s.%(funcName)s (%(filename)s:%(lineno)d) - %(message)s", )
    logger_formatter.converter = DateUtils.beijing_timetuple

    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)
    logger.setLevel(logging.INFO)
    return logger
