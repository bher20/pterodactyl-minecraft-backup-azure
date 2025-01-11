import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

class BackupLogger:
    VERBOSE = 15

    def __init__(self):
        # Define a new logging level
        logging.addLevelName(BackupLogger.VERBOSE, "VERBOSE")

        def verbose(self, message, *args, **kwargs):
            if self.isEnabledFor(BackupLogger.VERBOSE):
                self._log(BackupLogger.VERBOSE, message, args, **kwargs)

        logging.Logger.verbose = verbose

    def get_logger(self, name, level=logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logHandler = logging.StreamHandler()
        formatter = CustomJsonFormatter('%(timestamp)s %(name)s %(levelname)s %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)
        return logger