"""Centralized logging configuration for the application"""
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_file='discord_bot.log'):
    """Set up logging configuration for the application"""
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # Create and configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our configured handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set levels for specific modules
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('discord.client').setLevel(logging.DEBUG)
    logging.getLogger('discord.gateway').setLevel(logging.DEBUG)
    logging.getLogger('src.discord_tweet_handler').setLevel(logging.DEBUG)
    logging.getLogger('src.utils.ai_processor').setLevel(logging.DEBUG)

    # Return configured logger
    return root_logger