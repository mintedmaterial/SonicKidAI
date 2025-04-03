"""
Enhanced market service with Dune Analytics integration

This service extends the base market service to include on-chain data 
from Dune Analytics, allowing for more comprehensive market analysis.
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union, Tuple

from .dune_analytics_service import DuneAnalyticsService

# Setup logging
logger = logging.getLogger(__name__)

class MarketServiceWithDune:
    """
    Enhanced market service with Dune Analytics integration
    
    This service combines data from various sources including DexScreener
    and Dune Analytics to provide comprehensive market data.
    """
    
    def __init__(self, dune_service: DuneAnalyticsService = None):
        """
        Initialize the enhanced market service
        
        Args:
            dune_service: Optional DuneAnalyticsService instance
        """
        self.dune_service = dune_service or DuneAnalyticsService()
        self._initialized = False
        
        # Cache storage with TTL
        self.cache = {}
        # Default TTL values (in seconds)
        self.cache_ttls = {
            "dex_data": 600,  # 10 minutes
            "tvl_data": 600,  # 10 minutes
            "pairs": 300,     # 5 minutes
            "pools": 300,     # 5 minutes
        }
    
    async def initialize(self) -> bool:
        """Initialize the service and its dependencies"""
        if self._initialized:
            return True
            
        # Initialize Dune service
        dune_initialized = await self.dune_service.initialize()
        if not dune_initialized:
            logger.error("❌ Failed to initialize Dune Analytics service")
            return False
        
        self._initialized = True
        logger.info("✅ Market service with Dune initialized successfully")
        return True
    
    async def close(self):
        """Close the service and its dependencies"""
        if self.dune_service:
            await self.dune_service.close()
        self._initialized = False
    
    def _get_cache(self, cache_type: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get item from cache if it exists and is not expired
        
        Args:
            cache_type: Type of cache (dex_data, tvl_data, etc.)
            key: Cache key
            
        Returns:
            Cached data or None if not found or expired
        """
        cache_key = f"{cache_type}:{key}"
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            ttl = self.cache_ttls.get(cache_type, 300)  # Default 5 minutes
            if time.time() - timestamp < ttl:
                logger.info(f"✅ Using cached {cache_type} data for {key}")
                return data
        return None
    
    def _set_cache(self, cache_type: str, key: str, data: Dict[str, Any]):
        """
        Store item in cache with current timestamp
        
        Args:
            cache_type: Type of cache (dex_data, tvl_data, etc.)
            key: Cache key
            data: Data to cache
        """
        cache_key = f"{cache_type}:{key}"
        self.cache[cache_key] = (data, time.time())
    
    async def get_dex_data(self, dex_name: str) -> Optional[Dict[str, Any]]:
        """
        Get DEX trading data for a specific platform with caching
        
        Args:
            dex_name: Name of the DEX (e.g., "shadow", "metro")
            
        Returns:
            DEX data or None if failed
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return None
        
        # Check cache
        cached_data = self._get_cache("dex_data", dex_name)
        if cached_data:
            return cached_data
        
        # Get from Dune
        dex_data = await self.dune_service.get_dex_data(dex_name)
        if dex_data:
            self._set_cache("dex_data", dex_name, dex_data)
            return dex_data
            
        return None
    
    async def get_all_dexes_data(self) -> Dict[str, Any]:
        """
        Get trading data for all supported DEXes
        
        Returns:
            Dictionary with data for each DEX
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return {}
        
        # Get all supported DEXes
        dex_names = ["shadow", "metro", "beets"]
        
        # Fetch data for all DEXes in parallel
        tasks = [self.get_dex_data(dex) for dex in dex_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        dex_data = {}
        for i, result in enumerate(results):
            dex_name = dex_names[i]
            if isinstance(result, Exception):
                logger.error(f"❌ Error getting data for {dex_name}: {str(result)}")
                continue
            if result:
                dex_data[dex_name] = result
        
        return {"dexes": dex_data}
    
    async def get_sonic_tvl(self) -> Optional[Dict[str, Any]]:
        """
        Get Sonic TVL data with chart and caching
        
        Returns:
            Sonic TVL data or None if failed
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return None
        
        # Check cache
        cached_data = self._get_cache("tvl_data", "sonic")
        if cached_data:
            return cached_data
        
        # Get from Dune
        tvl_data = await self.dune_service.get_sonic_tvl()
        if tvl_data:
            self._set_cache("tvl_data", "sonic", tvl_data)
            return tvl_data
            
        return None
    
    async def search_pools(self, pool_id: str, dex_name: str = None) -> Dict[str, Any]:
        """
        Search for a specific pool by ID across DEXes with caching
        
        Args:
            pool_id: Pool ID or address
            dex_name: Optional DEX name to filter results
            
        Returns:
            Dictionary of pool data by DEX
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return {"pools": {}}
        
        # Create cache key
        cache_key = f"{pool_id}:{dex_name or 'all'}"
        
        # Check cache
        cached_data = self._get_cache("pools", cache_key)
        if cached_data:
            return cached_data
        
        # Get from Dune
        pool_data = await self.dune_service.search_pools(pool_id, dex_name)
        if pool_data and pool_data["pools"]:
            self._set_cache("pools", cache_key, pool_data)
            return pool_data
            
        return {"pools": {}}
    
    async def search_pairs(self, token_a: str, token_b: str = None, dex_name: str = None) -> Dict[str, Any]:
        """
        Search for token pairs across DEXes with caching
        
        Args:
            token_a: First token symbol
            token_b: Optional second token symbol
            dex_name: Optional DEX name to filter results
            
        Returns:
            Dictionary of pair data
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return {"records": []}
        
        # Create cache key
        if token_b:
            cache_key = f"{token_a}_{token_b}:{dex_name or 'all'}"
        else:
            cache_key = f"{token_a}:{dex_name or 'all'}"
        
        # Check cache
        cached_data = self._get_cache("pairs", cache_key)
        if cached_data:
            return cached_data
        
        # Get from Dune
        pair_data = await self.dune_service.search_pairs(token_a, token_b, dex_name)
        if pair_data and pair_data["records"]:
            self._set_cache("pairs", cache_key, pair_data)
            return pair_data
            
        return {"records": []}
    
    async def get_market_summary(self, token: str) -> Dict[str, Any]:
        """
        Get comprehensive market summary for a token combining multiple data sources
        
        Args:
            token: Token symbol (e.g., "WETH", "SONIC")
            
        Returns:
            Dictionary with market summary data
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return {"error": "Service initialization failed"}
        
        # Run queries in parallel for better performance
        tasks = [
            self.search_pairs(token),
            self.get_all_dexes_data()
        ]
        
        # Add Sonic TVL data if token is Sonic
        if token.upper() == "SONIC":
            tasks.append(self.get_sonic_tvl())
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        summary = {
            "token": token,
            "timestamp": int(time.time()),
            "sources": ["dune_analytics"]
        }
        
        # Process pairs data
        pairs_data = results[0] if not isinstance(results[0], Exception) else {"records": []}
        if pairs_data and pairs_data["records"]:
            summary["pairs"] = pairs_data["records"]
            summary["pair_count"] = len(pairs_data["records"])
            
            # Extract DEX distribution
            dex_counts = {}
            for pair in pairs_data["records"]:
                dex = pair.get("dex", "unknown")
                dex_counts[dex] = dex_counts.get(dex, 0) + 1
            summary["dex_distribution"] = dex_counts
        
        # Process DEX data
        dex_data = results[1] if not isinstance(results[1], Exception) else {"dexes": {}}
        if dex_data and "dexes" in dex_data:
            summary["dex_data"] = dex_data["dexes"]
        
        # Process TVL data for Sonic
        if token.upper() == "SONIC" and len(results) > 2:
            tvl_data = results[2] if not isinstance(results[2], Exception) else None
            if tvl_data:
                summary["tvl_data"] = tvl_data
        
        return summary
    
    async def get_dex_comparison(self) -> Dict[str, Any]:
        """
        Get comparison data for all supported DEXes
        
        Returns:
            Dictionary with comparison metrics
        """
        # Initialize if needed
        if not self._initialized:
            if not await self.initialize():
                return {"error": "Service initialization failed"}
        
        # Get data for all DEXes
        dex_data = await self.get_all_dexes_data()
        
        if not dex_data or "dexes" not in dex_data:
            return {"error": "Failed to retrieve DEX data"}
        
        # Process DEX data into comparison metrics
        comparison = {
            "timestamp": int(time.time()),
            "dexes": {}
        }
        
        for dex_name, data in dex_data["dexes"].items():
            if not data or "rows" not in data:
                continue
                
            # Extract key metrics for this DEX
            metrics = {
                "pair_count": len(data["rows"]),
                "total_volume_24h": 0,
                "total_tvl": 0,
                "avg_fee": 0,
                "unique_tokens": set()
            }
            
            # Calculate aggregate metrics
            fee_sum = 0
            fee_count = 0
            
            for row in data["rows"]:
                # Volume
                volume_24h = row.get("volume_24h", 0)
                if volume_24h:
                    metrics["total_volume_24h"] += float(volume_24h)
                
                # TVL
                tvl = row.get("tvl", 0)
                if tvl:
                    metrics["total_tvl"] += float(tvl)
                
                # Fee
                fee = row.get("fee", 0)
                if fee:
                    fee_sum += float(fee)
                    fee_count += 1
                
                # Unique tokens
                token0 = row.get("token0_symbol")
                token1 = row.get("token1_symbol")
                if token0:
                    metrics["unique_tokens"].add(token0)
                if token1:
                    metrics["unique_tokens"].add(token1)
            
            # Calculate average fee
            if fee_count > 0:
                metrics["avg_fee"] = fee_sum / fee_count
            
            # Convert set to count
            metrics["unique_token_count"] = len(metrics["unique_tokens"])
            del metrics["unique_tokens"]
            
            # Add to comparison data
            comparison["dexes"][dex_name] = metrics
        
        # Add comparison ratios
        comparison["comparisons"] = self._calculate_comparison_ratios(comparison["dexes"])
        
        return comparison
    
    def _calculate_comparison_ratios(self, dex_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comparison ratios between DEXes
        
        Args:
            dex_metrics: Dictionary of DEX metrics
            
        Returns:
            Dictionary with comparison ratios
        """
        comparisons = {}
        
        # Get list of DEXes
        dex_names = list(dex_metrics.keys())
        
        # Calculate TVL rank
        tvl_ranking = sorted(dex_names, key=lambda x: dex_metrics[x].get("total_tvl", 0), reverse=True)
        for i, dex in enumerate(tvl_ranking):
            if dex not in comparisons:
                comparisons[dex] = {}
            comparisons[dex]["tvl_rank"] = i + 1
        
        # Calculate volume rank
        volume_ranking = sorted(dex_names, key=lambda x: dex_metrics[x].get("total_volume_24h", 0), reverse=True)
        for i, dex in enumerate(volume_ranking):
            if dex not in comparisons:
                comparisons[dex] = {}
            comparisons[dex]["volume_rank"] = i + 1
        
        # Calculate volume/TVL ratio (higher is better)
        for dex in dex_names:
            tvl = dex_metrics[dex].get("total_tvl", 0)
            volume = dex_metrics[dex].get("total_volume_24h", 0)
            
            if tvl > 0:
                ratio = volume / tvl
            else:
                ratio = 0
                
            if dex not in comparisons:
                comparisons[dex] = {}
            comparisons[dex]["volume_tvl_ratio"] = ratio
        
        # Calculate market share percentages
        total_tvl = sum(dex_metrics[dex].get("total_tvl", 0) for dex in dex_names)
        total_volume = sum(dex_metrics[dex].get("total_volume_24h", 0) for dex in dex_names)
        
        for dex in dex_names:
            tvl = dex_metrics[dex].get("total_tvl", 0)
            volume = dex_metrics[dex].get("total_volume_24h", 0)
            
            if total_tvl > 0:
                tvl_share = (tvl / total_tvl) * 100
            else:
                tvl_share = 0
                
            if total_volume > 0:
                volume_share = (volume / total_volume) * 100
            else:
                volume_share = 0
                
            if dex not in comparisons:
                comparisons[dex] = {}
            comparisons[dex]["tvl_share_percent"] = tvl_share
            comparisons[dex]["volume_share_percent"] = volume_share
        
        return comparisons