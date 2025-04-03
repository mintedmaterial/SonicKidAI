"""Types for compatibility with schema.ts and database tables"""
from typing import Dict, Any

# Aliases for tables defined in schema.ts but not in schema.py
aiAnalysis = Dict[str, Any]
dashboardPosts = Dict[str, Any]
marketUpdates = Dict[str, Any]
whaleAlerts = Dict[str, Any]
telegramChannels = Dict[str, Any]