import logging
from datetime import datetime
import pytz

# Custom formatter class for logging with local time
class LocalTimeFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, timezone='America/Chicago'):
        super().__init__(fmt, datefmt)
        self.timezone = pytz.timezone(timezone)

    def converter(self, timestamp):
        # Convert UTC timestamp to local time
        dt = datetime.fromtimestamp(timestamp, self.timezone)
        return dt

    def formatTime(self, record, datefmt=None):
        # Override the default time format method to use local timezone
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

# Function to set up logger with local time formatter
def setup_local_time_logger(name="DoorSensors", level=logging.INFO, timezone='America/Chicago'):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create a console handler
    ch = logging.StreamHandler()
    
    # Create and set the local time formatter
    formatter = LocalTimeFormatter('%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', timezone=timezone)
    ch.setFormatter(formatter)

    # Add the handler to the logger
    if not logger.handlers:  # Avoid adding multiple handlers
        logger.addHandler(ch)

    return logger
