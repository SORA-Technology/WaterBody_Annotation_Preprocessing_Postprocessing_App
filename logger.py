import logging
from colorama import Fore, Style, init
import os

# Initialize colorama
init(autoreset=True)

# Define a custom log level for SUCCESS
SUCCESS_LEVEL = 25  # Define a custom log level between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

# Add the success method to the logging.Logger class
def success(self, message, *args, **kwargs):
    """Log a success message."""
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)

logging.Logger.success = success


class CustomFormatter(logging.Formatter):
    """Custom Formatter for colored logging."""
    LOG_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.YELLOW,  # Changed INFO color to blue
        logging.WARNING: Fore.BLUE,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
        SUCCESS_LEVEL: Fore.GREEN,  # Changed SUCCESS color to green
    }

    def format(self, record):
        log_color = self.LOG_COLORS.get(record.levelno, "")
        log_message = super().format(record)
        return f"{log_color}{log_message}{Style.RESET_ALL}"


def Logger(name: str = "ColoredLogger", log_file: str = "file.log") -> logging.Logger:
    """Get a configured logger with color support and file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Adjust the log level as needed

    if not logger.hasHandlers():
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Set formatter for console output
        console_formatter = CustomFormatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_formatter)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Set formatter for file output (no color)
        file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


# Example usage
# if __name__ == "__main__":
#     log_file_path = os.path.join(os.getcwd(), "file.log")
#     logger = Logger("MyLogger: ", log_file=log_file_path)
    
#     # Example log messages
#     logger.debug("This is a DEBUG message.")
#     logger.info("This is an INFO message.")  # INFO messages now appear in blue
#     logger.success("This is a SUCCESS message.")  # SUCCESS messages now appear in green
#     logger.warning("This is a WARNING message.")
#     logger.error("This is an ERROR message.")
#     logger.critical("This is a CRITICAL message.")
