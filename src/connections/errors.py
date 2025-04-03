"""Custom error classes for Sonic connections"""

class SonicConnectionError(Exception):
    """Base exception for Sonic connection errors"""
    pass

class ConnectionError(SonicConnectionError):
    """Base class for connection-related errors"""
    pass

class SonicSwapError(SonicConnectionError):
    """Exception for swap-related errors"""
    pass

class SonicTransferError(SonicConnectionError):
    """Exception for transfer-related errors"""
    pass

class SonicQuoteError(SonicConnectionError):
    """Exception for quote-related errors"""
    pass