"""Storage module initialization"""
from .base import BaseStorage
from .storage_service import StorageService

storage = StorageService()

__all__ = ['storage', 'BaseStorage']
