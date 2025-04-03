"""
Dune Analytics API integration service

This service provides data from Dune Analytics for various DeFi platforms
including Shadow, Metro, Sonic, and Beets.
"""
import os
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
import aiohttp

# Setup logging
logger = logging.getLogger(__name__)

class DuneAnalyticsService:
    """Service for Dune Analytics API integration"""
    
    # Query ID constants for different dexes
    QUERY_IDS = {
        "shadow": 4659701,  # Shadow Exchange query ID
        "shadow_exchange": 4659701,  # Shadow Exchange query ID (backward compatibility)
        "sonic_tvl": 4800942,  # Sonic TVL query ID
        "metro": 4901234,  # Metro query ID (placeholder - update with actual ID)
        "beets": 4982312,  # Beets query ID (placeholder - update with actual ID)
    }
    
    # Base URLs
    API_BASE_URL = "https://api.dune.com/api/v1"
    
    def __init__(self, api_key: str = None, timeout: int = 300, max_retries: int = 5, 
                 poll_interval: int = 2):
        """
        Initialize Dune Analytics service
        
        Args:
            api_key: Dune API key, if None will be loaded from environment
            timeout: Timeout for query execution in seconds (Dune can be slow)
            max_retries: Maximum number of retries for polling query status
            poll_interval: Seconds between query status checks
        """
        self.api_key = api_key or os.getenv("DUNE_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.poll_interval = poll_interval
        self.session = None
        self._initialized = False
        
        # Cache for query results with TTL in seconds
        self.cache = {}
        self.cache_ttl = 600  # 10 minutes default TTL
    
    async def initialize(self) -> bool:
        """Initialize the service and validate API key"""
        if self._initialized:
            return True
            
        if not self.api_key:
            logger.error("No Dune API key provided or found in environment")
            return False
        
        # Create session
        self.session = aiohttp.ClientSession()
        self._initialized = True
        
        # Optional: validate API key
        try:
            # Try to execute a simple query to validate API key
            query_id = self.QUERY_IDS.get("shadow")
            if query_id:
                headers = {"x-dune-api-key": self.api_key}
                status_url = f"{self.API_BASE_URL}/query/{query_id}/execute"
                
                async with self.session.post(status_url, headers=headers) as response:
                    if response.status == 200:
                        logger.info("✅ Dune API key validated successfully")
                        return True
                    elif response.status == 401:
                        error_text = await response.text()
                        logger.error(f"❌ Invalid Dune API key: {error_text}")
                        return False
                    else:
                        # Could be other errors not related to auth
                        logger.warning(f"⚠️ Dune API warning (status {response.status})")
                        return True
            return True
        except Exception as e:
            logger.error(f"❌ Error validating Dune API key: {str(e)}")
            return False
    
    async def close(self):
        """Close the session and clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()
        self._initialized = False
    
    async def execute_query(self, query_id: int, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a Dune query and wait for results
        
        Args:
            query_id: Dune query ID
            params: Optional parameters for the query
            
        Returns:
            Query results or None if failed
        """
        if not self._initialized:
            if not await self.initialize():
                return None
        
        # Check cache first
        cache_key = f"query_{query_id}_{str(params) if params else 'no_params'}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"✅ Using cached Dune data for query ID {query_id}")
                return cached_data
        
        # Execute query
        try:
            headers = {"x-dune-api-key": self.api_key}
            url = f"{self.API_BASE_URL}/query/{query_id}/execute"
            data = params if params else {}
            
            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to execute query {query_id}: {error_text}")
                    return None
                
                # Get execution ID
                result = await response.json()
                if "execution_id" not in result:
                    logger.error(f"❌ No execution ID in response: {result}")
                    return None
                
                execution_id = result["execution_id"]
                logger.info(f"✅ Query {query_id} execution started with ID: {execution_id}")
                
                # Wait for query execution to complete
                return await self._wait_for_query_results(execution_id)
                
        except Exception as e:
            logger.error(f"❌ Error executing Dune query {query_id}: {str(e)}")
            return None
    
    async def _wait_for_query_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Wait for query execution to complete
        
        Args:
            execution_id: Dune execution ID
            
        Returns:
            Query results or None if failed or timed out
        """
        start_time = time.time()
        status_url = f"{self.API_BASE_URL}/execution/{execution_id}/status"
        results_url = f"{self.API_BASE_URL}/execution/{execution_id}/results"
        headers = {"x-dune-api-key": self.api_key}
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Check if we've exceeded timeout
                if time.time() - start_time > self.timeout:
                    logger.error(f"❌ Query execution timed out after {self.timeout} seconds")
                    return None
                
                # Check execution status
                logger.info(f"Query execution in progress, waiting... (Attempt {attempt}/{self.max_retries})")
                async with self.session.get(status_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"⚠️ Failed to get execution status: {error_text}")
                        await asyncio.sleep(self.poll_interval)
                        continue
                    
                    status_data = await response.json()
                    state = status_data.get("state", "UNKNOWN")
                    
                    if state == "QUERY_STATE_COMPLETED":
                        # Query completed, get results
                        return await self._get_query_results(results_url, headers)
                    
                    elif state == "QUERY_STATE_FAILED":
                        logger.error(f"❌ Query execution failed: {status_data}")
                        return None
                    
                    elif state in ["QUERY_STATE_PENDING", "QUERY_STATE_EXECUTING"]:
                        # Still executing, wait for next check
                        queue_position = status_data.get("queue_position", "unknown")
                        
                        if state == "QUERY_STATE_PENDING":
                            logger.info(f"Query pending in queue position: {queue_position}")
                        else:
                            logger.info("Query executing...")
                        
                        # Wait before checking again
                        await asyncio.sleep(self.poll_interval)
                        continue
                    
                    else:
                        logger.warning(f"⚠️ Unknown query state: {state}")
                        await asyncio.sleep(self.poll_interval)
                        continue
                    
            except Exception as e:
                logger.error(f"❌ Error checking query status: {str(e)}")
                await asyncio.sleep(self.poll_interval)
        
        logger.error(f"❌ Maximum retries ({self.max_retries}) exceeded waiting for query results")
        return None
    
    async def _get_query_results(self, results_url: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Get the results for a completed query
        
        Args:
            results_url: URL for query results
            headers: Request headers
            
        Returns:
            Query results or None if failed
        """
        try:
            async with self.session.get(results_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to get query results: {error_text}")
                    return None
                
                results = await response.json()
                logger.info("✅ Query results retrieved successfully")
                
                # Cache the results
                cache_key = results_url.split("/")[-2]  # Use execution_id as key
                self.cache[cache_key] = (results, time.time())
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error getting query results: {str(e)}")
            return None
    
    async def get_dex_data(self, dex_name: str) -> Optional[Dict[str, Any]]:
        """
        Get DEX trading data for a specific platform
        
        Args:
            dex_name: Name of the DEX (e.g., "shadow", "metro")
            
        Returns:
            DEX data or None if failed
        """
        # Convert to lowercase for case-insensitive matching
        dex_name = dex_name.lower()
        
        # Check if DEX is supported
        if dex_name not in self.QUERY_IDS:
            logger.warning(f"⚠️ Unsupported DEX: {dex_name}")
            return None
        
        # Execute query
        query_id = self.QUERY_IDS[dex_name]
        return await self.execute_query(query_id)
    
    async def get_sonic_tvl(self) -> Optional[Dict[str, Any]]:
        """
        Get Sonic TVL data with chart
        
        Returns:
            Sonic TVL data or None if failed
        """
        query_id = self.QUERY_IDS.get("sonic_tvl")
        if not query_id:
            logger.warning("⚠️ Sonic TVL query ID not found")
            return None
        
        return await self.execute_query(query_id)
    
    async def search_pools(self, pool_id: str, dex_name: str = None) -> Dict[str, Any]:
        """
        Search for a specific pool by ID across DEXes
        
        Args:
            pool_id: Pool ID or address
            dex_name: Optional DEX name to filter results
            
        Returns:
            Dictionary of pool data by DEX
        """
        results = {"pools": {}}
        
        # Get data for requested DEX or all DEXes
        dex_list = [dex_name] if dex_name else ["shadow", "metro", "beets"]
        
        for dex in dex_list:
            if dex.lower() not in self.QUERY_IDS:
                continue
                
            dex_data = await self.get_dex_data(dex)
            if not dex_data or "rows" not in dex_data:
                continue
            
            # Extract pool data
            dex_pools = [row for row in dex_data["rows"] if str(row.get("pool_id", "")).lower() == pool_id.lower()]
            
            if dex_pools:
                results["pools"][dex] = dex_pools
        
        return results
    
    async def search_pairs(self, token_a: str, token_b: str = None, dex_name: str = None) -> Dict[str, Any]:
        """
        Search for token pairs across DEXes
        
        Args:
            token_a: First token symbol
            token_b: Optional second token symbol
            dex_name: Optional DEX name to filter results
            
        Returns:
            Dictionary of pair data
        """
        results = {"records": []}
        
        # Get data for requested DEX or all DEXes
        dex_list = [dex_name] if dex_name else ["shadow", "metro", "beets"]
        
        for dex in dex_list:
            if dex.lower() not in self.QUERY_IDS:
                continue
                
            dex_data = await self.get_dex_data(dex)
            if not dex_data or "rows" not in dex_data:
                continue
            
            # Extract pair data
            if token_b:
                # Find pairs with both tokens
                pairs = [
                    row for row in dex_data["rows"] 
                    if (token_a.upper() in str(row.get("token0_symbol", "")).upper() and 
                        token_b.upper() in str(row.get("token1_symbol", "")).upper()) or
                       (token_b.upper() in str(row.get("token0_symbol", "")).upper() and 
                        token_a.upper() in str(row.get("token1_symbol", "")).upper())
                ]
            else:
                # Find pairs with just token A
                pairs = [
                    row for row in dex_data["rows"] 
                    if token_a.upper() in str(row.get("token0_symbol", "")).upper() or
                       token_a.upper() in str(row.get("token1_symbol", "")).upper()
                ]
            
            # Add DEX name to each record
            for pair in pairs:
                pair["dex"] = dex
                results["records"].append(pair)
        
        return results