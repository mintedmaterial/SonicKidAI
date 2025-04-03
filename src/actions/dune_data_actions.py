"""
Dune Analytics data actions for querying and processing on-chain metrics
"""
import logging
from typing import Dict, List, Any, Optional, Union
import pandas as pd

from ..services.dune_analytics_service import DuneAnalyticsService

logger = logging.getLogger(__name__)

class DuneDataActions:
    """Actions for processing Dune Analytics data"""
    
    def __init__(self, dune_service: DuneAnalyticsService):
        """Initialize with Dune Analytics service

        Args:
            dune_service: Dune Analytics service instance
        """
        self.dune_service = dune_service
        
    async def find_pool_by_id(self, pool_id: str, dex: Optional[str] = None) -> Dict[str, Any]:
        """Find pool by ID across DEXes or in a specific DEX

        Args:
            pool_id: Pool ID to search for
            dex: Optional DEX name to limit search to
            
        Returns:
            Dictionary with pool data
        """
        try:
            logger.info(f"Searching for pool {pool_id}" + (f" on {dex}" if dex else " across all DEXes"))
            
            return await self.dune_service.search_pools(pool_id, dex)
        except Exception as e:
            logger.error(f"❌ Error finding pool by ID: {str(e)}")
            return {"error": str(e)}
    
    async def find_pair_data(self, token_a: str, token_b: Optional[str] = None, dex: Optional[str] = None) -> Dict[str, Any]:
        """Find pair data for tokens across DEXes or in a specific DEX

        Args:
            token_a: First token symbol
            token_b: Optional second token symbol
            dex: Optional DEX name to limit search to
            
        Returns:
            Dictionary with pair data
        """
        try:
            tokens_display = f"{token_a}" + (f"/{token_b}" if token_b else "")
            logger.info(f"Searching for pair {tokens_display}" + (f" on {dex}" if dex else " across all DEXes"))
            
            return await self.dune_service.search_pairs(token_a, token_b, dex)
        except Exception as e:
            logger.error(f"❌ Error finding pair data: {str(e)}")
            return {"error": str(e)}
    
    async def get_dex_summary(self, dex_name: str) -> Dict[str, Any]:
        """Get summary data for a specific DEX

        Args:
            dex_name: DEX name (shadow, sonic, metro, beets)
            
        Returns:
            Dictionary with DEX summary data
        """
        try:
            logger.info(f"Getting summary data for {dex_name} DEX")
            
            # Standardize DEX name
            dex_name = dex_name.lower()
            
            # Get DEX data
            df = await self.dune_service.get_dex_data(dex_name)
            
            if df is None or df.empty:
                logger.warning(f"⚠️ No data returned for DEX {dex_name}")
                return {"error": f"No data available for {dex_name.capitalize()} DEX"}
            
            result = {}
            
            # Extract and process data based on DEX type
            if dex_name == 'shadow':
                # Process Shadow Exchange data
                result = self._process_shadow_data(df)
            elif dex_name == 'sonic':
                # Process Sonic TVL data
                result = self._process_sonic_data(df)
            elif dex_name == 'metro':
                # Process Metro pools data
                result = self._process_metro_data(df)
            elif dex_name == 'beets':
                # Process Beets pools data
                result = self._process_beets_data(df)
            else:
                # Unknown DEX
                return {"error": f"Unknown DEX: {dex_name}"}
            
            logger.info(f"✅ Successfully processed {dex_name} DEX data")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting DEX summary: {str(e)}")
            return {"error": str(e)}
    
    def _process_shadow_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process Shadow DEX data

        Args:
            df: DataFrame with Shadow data
            
        Returns:
            Dictionary with processed data
        """
        result = {}
        
        try:
            # Extract TVL data if available
            if 'tvl' in df.columns or 'tvl_usd' in df.columns:
                tvl_col = 'tvl' if 'tvl' in df.columns else 'tvl_usd'
                tvl_data = df[tvl_col].astype(float)
                
                # Calculate latest TVL
                latest_tvl = tvl_data.iloc[-1] if not tvl_data.empty else 0
                
                # Calculate 24h change
                if len(tvl_data) > 1:
                    prev_tvl = tvl_data.iloc[-2]
                    tvl_change_24h = ((latest_tvl - prev_tvl) / prev_tvl) * 100 if prev_tvl > 0 else 0
                else:
                    tvl_change_24h = 0
                
                result['tvl'] = {
                    'latest_tvl': latest_tvl,
                    'tvl_change_24h': tvl_change_24h
                }
            
            # Extract volume data if available
            volume_cols = [col for col in df.columns if 'volume' in col.lower()]
            if volume_cols:
                volume_col = volume_cols[0]
                volume_data = df[volume_col].astype(float)
                
                # Calculate total volume
                total_volume = volume_data.sum()
                
                # Calculate 24h volume if timestamp data is available
                if 'timestamp' in df.columns or 'date' in df.columns or 'time' in df.columns:
                    time_col = next(col for col in ['timestamp', 'date', 'time'] if col in df.columns)
                    df = df.sort_values(by=time_col)
                    
                    # Get the last 24h of data
                    last_time = df[time_col].iloc[-1]
                    
                    # Depending on the time format, filter last 24h differently
                    if 'date' in time_col or 'time' in time_col:
                        from datetime import datetime, timedelta
                        if isinstance(last_time, str):
                            last_time = pd.to_datetime(last_time)
                        day_ago = last_time - timedelta(days=1)
                        last_24h = df[df[time_col] >= day_ago]
                    else:
                        # Assume timestamp in seconds
                        day_in_seconds = 24 * 60 * 60
                        last_24h = df[df[time_col] >= (last_time - day_in_seconds)]
                    
                    volume_24h = last_24h[volume_col].astype(float).sum()
                else:
                    # If no timestamp, just use the last row
                    volume_24h = volume_data.iloc[-1] if not volume_data.empty else 0
                
                result['volume'] = {
                    'total_volume_usd': total_volume,
                    'volume_24h_usd': volume_24h
                }
            
            # Extract pool data if available
            if 'pool_count' in df.columns:
                pool_count = df['pool_count'].iloc[-1]
                result['pools'] = {
                    'pool_count': pool_count
                }
                
            # Check for swap fees
            fee_cols = [col for col in df.columns if 'fee' in col.lower()]
            if fee_cols:
                fee_col = fee_cols[0]
                fees_data = df[fee_col].astype(float)
                
                # Calculate total fees
                total_fees = fees_data.sum()
                
                result['fees'] = {
                    'total_fees_usd': total_fees
                }
            
            return result
        except Exception as e:
            logger.error(f"❌ Error processing Shadow data: {str(e)}")
            return {"error": str(e)}
    
    def _process_sonic_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process Sonic TVL data

        Args:
            df: DataFrame with Sonic data
            
        Returns:
            Dictionary with processed data
        """
        result = {}
        
        try:
            # Extract TVL data
            if 'tvl' in df.columns:
                df = df.sort_values(by='date' if 'date' in df.columns else df.columns[0])
                tvl_data = df['tvl'].astype(float)
                
                # Calculate latest TVL
                latest_tvl = tvl_data.iloc[-1] if not tvl_data.empty else 0
                
                # Calculate 24h change
                if len(tvl_data) > 1:
                    prev_tvl = tvl_data.iloc[-2]
                    tvl_change_24h = ((latest_tvl - prev_tvl) / prev_tvl) * 100 if prev_tvl > 0 else 0
                else:
                    tvl_change_24h = 0
                
                result['tvl'] = {
                    'latest_tvl': latest_tvl,
                    'tvl_change_24h': tvl_change_24h
                }
            
            # Extract transaction data if available
            tx_cols = [col for col in df.columns if 'tx' in col.lower() or 'transaction' in col.lower()]
            if tx_cols:
                tx_col = tx_cols[0]
                tx_data = df[tx_col].astype(float)
                
                # Calculate total transactions
                total_tx = tx_data.sum()
                
                result['transactions'] = {
                    'total_transactions': total_tx
                }
            
            return result
        except Exception as e:
            logger.error(f"❌ Error processing Sonic data: {str(e)}")
            return {"error": str(e)}
    
    def _process_metro_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process Metro pools data

        Args:
            df: DataFrame with Metro data
            
        Returns:
            Dictionary with processed data
        """
        result = {}
        
        try:
            # Count pools
            pool_count = len(df) if not df.empty else 0
            
            # Sum TVL across all pools if available
            tvl_cols = [col for col in df.columns if 'tvl' in col.lower() or 'liquidity' in col.lower()]
            if tvl_cols:
                tvl_col = tvl_cols[0]
                total_tvl = df[tvl_col].astype(float).sum()
                result['tvl'] = {
                    'total_tvl': total_tvl
                }
            
            # Sum volume across all pools if available
            volume_cols = [col for col in df.columns if 'volume' in col.lower()]
            if volume_cols:
                volume_col = volume_cols[0]
                total_volume = df[volume_col].astype(float).sum()
                
                # Try to find 24h volume
                volume_24h_cols = [col for col in df.columns if 'volume_24h' in col.lower() or 'volume_1d' in col.lower()]
                if volume_24h_cols:
                    volume_24h_col = volume_24h_cols[0]
                    total_volume_24h = df[volume_24h_col].astype(float).sum()
                else:
                    total_volume_24h = None
                
                volume_data = {
                    'total_volume_usd': total_volume
                }
                
                if total_volume_24h is not None:
                    volume_data['total_volume_24h'] = total_volume_24h
                
                result['volume'] = volume_data
            
            # Calculate average APR if available
            apr_cols = [col for col in df.columns if 'apr' in col.lower() or 'apy' in col.lower() or 'yield' in col.lower()]
            if apr_cols:
                apr_col = apr_cols[0]
                avg_apr = df[apr_col].astype(float).mean()
                result['yield'] = {
                    'average_apr': avg_apr
                }
            
            # Add metrics section
            result['metrics'] = {
                'pool_count': pool_count
            }
            
            # Add volume_24h to metrics if available
            if 'volume' in result and 'total_volume_24h' in result['volume']:
                result['metrics']['total_volume_24h'] = result['volume']['total_volume_24h']
            
            return result
        except Exception as e:
            logger.error(f"❌ Error processing Metro data: {str(e)}")
            return {"error": str(e)}
    
    def _process_beets_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process Beets pools data

        Args:
            df: DataFrame with Beets data
            
        Returns:
            Dictionary with processed data
        """
        result = {}
        
        try:
            # Count pools
            pool_count = len(df) if not df.empty else 0
            
            # Sum TVL across all pools if available
            tvl_cols = [col for col in df.columns if 'tvl' in col.lower() or 'liquidity' in col.lower()]
            if tvl_cols:
                tvl_col = tvl_cols[0]
                total_tvl = df[tvl_col].astype(float).sum()
                result['tvl'] = {
                    'total_tvl': total_tvl
                }
            
            # Sum volume across all pools if available
            volume_cols = [col for col in df.columns if 'volume' in col.lower()]
            if volume_cols:
                volume_col = volume_cols[0]
                total_volume = df[volume_col].astype(float).sum()
                
                # Try to find 24h volume
                volume_24h_cols = [col for col in df.columns if 'volume_24h' in col.lower() or 'volume_1d' in col.lower()]
                if volume_24h_cols:
                    volume_24h_col = volume_24h_cols[0]
                    total_volume_24h = df[volume_24h_col].astype(float).sum()
                else:
                    total_volume_24h = None
                
                volume_data = {
                    'total_volume_usd': total_volume
                }
                
                if total_volume_24h is not None:
                    volume_data['total_volume_24h'] = total_volume_24h
                
                result['volume'] = volume_data
            
            # Calculate average APR if available
            apr_cols = [col for col in df.columns if 'apr' in col.lower() or 'apy' in col.lower() or 'yield' in col.lower()]
            if apr_cols:
                apr_col = apr_cols[0]
                avg_apr = df[apr_col].astype(float).mean()
                result['yield'] = {
                    'average_apr': avg_apr
                }
            
            # Add fees data if available
            fee_cols = [col for col in df.columns if 'fee' in col.lower()]
            if fee_cols:
                fee_col = fee_cols[0]
                avg_fee = df[fee_col].astype(float).mean()
                result['fees'] = {
                    'average_fee': avg_fee
                }
            
            # Add metrics section
            result['metrics'] = {
                'pool_count': pool_count
            }
            
            # Add volume_24h to metrics if available
            if 'volume' in result and 'total_volume_24h' in result['volume']:
                result['metrics']['total_volume_24h'] = result['volume']['total_volume_24h']
            
            return result
        except Exception as e:
            logger.error(f"❌ Error processing Beets data: {str(e)}")
            return {"error": str(e)}