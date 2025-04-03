"""
Whale Tracker Service - monitors and analyzes whale wallet activities
"""
import logging
import asyncio
import time
import json
import websockets
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
import asyncpg
from ..constants.chain_config import ChainConfig, CHAIN_CONFIG
from ..server.db import Database

logger = logging.getLogger(__name__)

class WhaleTrackerService:
    """Service for tracking and analyzing whale wallet activities"""
    
    # List of tracked whale wallets - starting with the ones from the user request
    WHALE_WALLETS = [
        "0xAdDbD648c380E4822e9c934B0fc5C9f607d892c5",
        "0x7e11cd6f2e24ddec67246a35dda4afc62dad6922",
        "0xcdFF6DDc9f095CeDF3b1529e3B961a39iEb75F0",
        "0xc53127AF07fF9a749BA8b70B6BF5f0899E4F33dE",
        "0x3eE607990BfB250B03b9656E0Ed2F9Bb9F64f867",
        "0xeCAD53cDB102Bd84Efb050E7F406b081D9E7E2Ae",
        "0x996f77356278269347aa2310f8a4e1855b7c3c37",
        "0x67A5D82F02724E01F02D0aA9173E4D8E8aE6a78a",
        "0x5b43e0a357B4d6a60b7e757C1F345bE3Bcd1Af6A",
        "0x8aE8be9F23Ff6B397E85Dd9219F934805b76E07d",
        "0x91Ef84244Aa478c39E966B9d18Bd7FD8562576f7",
        "0x5a6d63fF791c3eDcfA6eF3087B3cB9e5052bd332",
        "0x64774Eff5A31C85070F158C6DaC0e12cEB2b1C11",
        "0x8BEa04A94903f97A5c0cFac79F9b24EA25734358",
        "0x7A2AB74416Fb2Bb3D5497918529638702c137841",
        "0x52faCd14353E4F9d16b84A9352A7f6e8e0C12B27",
        "0x98C3e9D7508461B0C3222a3Dd0dA2bA4e9867B2C",
        "0x2C7036574e5a8b3c4cE6d077D2332e50c3Ba5518",
        "0x63A8CE2F72bd30c1Fb8660DF44D22F733e2161e7",
        "0x7F2b28C0Ef0f793d48a41c3407BbdD13b3A39a89",
        "0x3F5a1BFFB1Aa864af7E826Fb8fcf4e7471d97319",
        "0xee97F4229194e3D7829D896DdFF6242Fc298A998",
        "0xc4fc550ca25de0ba3baf9a9dc85bab2c211f0f39",
        # Additional well-known whale wallets can be added here
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize whale tracker service"""
        self.config = config or {}
        self.db = self.config.get('db')
        self.crypto_panic = self.config.get('crypto_panic')
        self.huggingface = self.config.get('huggingface')
        self.session = None
        self.running = False
        self.update_interval = self.config.get('update_interval', 60 * 15)  # 15 minutes default
        self.whale_threshold = self.config.get('whale_threshold', 100000)  # $100k USD default
        self.tx_cache = {}
        self.monitored_addresses = set(self.WHALE_WALLETS)
        
    async def initialize(self) -> bool:
        """Initialize the service and its dependencies"""
        try:
            # Connect to database
            if self.db:
                await self.db.connect()
                
            # Initialize CryptoPanic service if available
            if self.crypto_panic:
                await self.crypto_panic.initialize()
            
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Create database tables if they don't exist
            await self._ensure_tables_exist()
            
            logger.info(f"Initialized whale tracker with {len(self.monitored_addresses)} addresses")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize whale tracker: {str(e)}")
            return False
    
    async def _ensure_tables_exist(self) -> None:
        """Ensure that the necessary database tables exist"""
        if not self.db:
            logger.warning("No database connection available for whale tracker")
            return
        
        # Create tables if they don't exist
        tables_query = """
        -- Table for whale wallet addresses
        CREATE TABLE IF NOT EXISTS whale_addresses (
            address TEXT PRIMARY KEY,
            label TEXT,
            tags TEXT[],
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table for whale transactions
        CREATE TABLE IF NOT EXISTS whale_transactions (
            tx_hash TEXT PRIMARY KEY,
            block_number BIGINT,
            from_address TEXT,
            to_address TEXT,
            token_address TEXT,
            token_symbol TEXT,
            amount NUMERIC,
            amount_usd NUMERIC,
            timestamp TIMESTAMP,
            chain_id TEXT,
            tx_type TEXT
        );
        
        -- Table for whale wallet balances
        CREATE TABLE IF NOT EXISTS whale_balances (
            id SERIAL PRIMARY KEY,
            address TEXT,
            token_address TEXT,
            token_symbol TEXT,
            amount NUMERIC,
            amount_usd NUMERIC,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(address, token_address)
        );
        """
        
        await self.db.raw_query(tables_query)
        
        # Populate initial whale addresses
        if self.monitored_addresses:
            values = []
            for address in self.monitored_addresses:
                values.append(f"('{address}', 'Tracked Whale', ARRAY['whale'])")
            
            if values:
                values_str = ', '.join(values)
                insert_query = f"""
                INSERT INTO whale_addresses (address, label, tags)
                VALUES {values_str}
                ON CONFLICT (address) DO NOTHING;
                """
                await self.db.raw_query(insert_query)
    
    async def start_monitoring(self) -> None:
        """Start the background monitoring process"""
        if self.running:
            logger.warning("Whale tracker monitoring is already running")
            return
        
        self.running = True
        logger.info("Starting whale tracker monitoring")
        
        # Start the monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for whale tracking"""
        while self.running:
            try:
                # Run a monitoring cycle
                await self._run_monitoring_cycle()
                
                # Analyze recent patterns
                await self._analyze_whale_patterns()
                
                # Sleep until next update
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in whale monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Sleep for a minute before retrying
    
    async def _run_monitoring_cycle(self) -> None:
        """Run a single monitoring cycle"""
        logger.info("Running whale monitoring cycle")
        
        # Get the current list of monitored addresses
        await self._refresh_monitored_addresses()
        
        # Get transactions for monitored addresses
        for address in self.monitored_addresses:
            try:
                # Get transactions for this address
                transactions = await self._get_address_transactions(address)
                
                # Process new transactions
                if transactions:
                    await self._process_transactions(transactions, address)
                
                # Get current wallet balances
                await self._update_wallet_balances(address)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error monitoring address {address}: {str(e)}")
    
    async def _refresh_monitored_addresses(self) -> None:
        """Refresh the list of monitored addresses from the database"""
        if not self.db:
            return
        
        try:
            # Query the database for all tracked addresses
            query = "SELECT address FROM whale_addresses;"
            result = await self.db.raw_query(query)
            
            if result and 'rows' in result:
                # Update the monitored addresses set
                addresses = {row['address'] for row in result['rows']}
                
                # Merge with the hardcoded list to ensure we don't lose anything
                addresses.update(self.WHALE_WALLETS)
                
                self.monitored_addresses = addresses
                logger.debug(f"Refreshed monitored addresses: {len(self.monitored_addresses)} total")
        except Exception as e:
            logger.error(f"Error refreshing monitored addresses: {str(e)}")
    
    async def _get_address_transactions(self, address: str) -> List[Dict[str, Any]]:
        """Get transactions for a specific address"""
        if not self.session:
            return []
        
        # Use different APIs based on chain
        chain_id = 'sonic'  # Default to Sonic chain
        
        # Different endpoints for different chains
        if chain_id == 'sonic':
            url = f"https://explorer-api.sonicscan.org/api?module=account&action=txlist&address={address}&sort=desc&limit=50"
        elif chain_id in ('ethereum', 'eth'):
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={self.config.get('etherscan_key', '')}"
        else:
            logger.warning(f"Unsupported chain ID for transaction fetching: {chain_id}")
            return []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching transactions for {address}: HTTP {response.status}")
                    return []
                
                data = await response.json()
                
                if data.get('status') != '1' and data.get('message') != 'OK':
                    logger.error(f"API error for {address}: {data.get('message')}")
                    return []
                
                # Extract and format transactions
                transactions = []
                for tx in data.get('result', []):
                    # Skip contract creations and failed transactions
                    if tx.get('to') == '' or tx.get('isError') == '1':
                        continue
                    
                    # Get token information if it's a token transfer
                    token_info = await self._get_token_info(tx.get('contractAddress'), chain_id) if tx.get('contractAddress') else None
                    
                    transaction = {
                        'tx_hash': tx.get('hash'),
                        'block_number': int(tx.get('blockNumber', 0)),
                        'from_address': tx.get('from', '').lower(),
                        'to_address': tx.get('to', '').lower(),
                        'value': float(tx.get('value', 0)) / 1e18,  # Convert to ETH/SONIC
                        'token_address': tx.get('contractAddress', '').lower() if tx.get('contractAddress') else None,
                        'token_symbol': token_info.get('symbol') if token_info else None,
                        'timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                        'chain_id': chain_id,
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': float(tx.get('gasPrice', 0)) / 1e9  # Convert to Gwei
                    }
                    
                    transactions.append(transaction)
                
                return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {str(e)}")
            return []
    
    async def _get_token_info(self, token_address: str, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get token information for a specific contract address"""
        if not token_address or not self.session:
            return None
        
        # First, check if we already have this token cached
        cache_key = f"{chain_id}:{token_address}"
        if cache_key in self.tx_cache:
            return self.tx_cache[cache_key]
        
        # Different endpoints for different chains
        if chain_id == 'sonic':
            url = f"https://explorer-api.sonicscan.org/api?module=token&action=getToken&contractaddress={token_address}"
        elif chain_id in ('ethereum', 'eth'):
            # For Ethereum, we'd need to use a token API or a hardcoded list
            # This is a simplified approach
            url = f"https://api.etherscan.io/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={self.config.get('etherscan_key', '')}"
        else:
            logger.warning(f"Unsupported chain ID for token info: {chain_id}")
            return None
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching token info for {token_address}: HTTP {response.status}")
                    return None
                
                data = await response.json()
                
                if data.get('status') != '1' and data.get('message') != 'OK':
                    logger.error(f"API error for token {token_address}: {data.get('message')}")
                    return None
                
                # Extract and format token info
                token_data = data.get('result', {})
                
                if isinstance(token_data, list) and len(token_data) > 0:
                    token_data = token_data[0]
                
                token_info = {
                    'address': token_address.lower(),
                    'name': token_data.get('name', 'Unknown Token'),
                    'symbol': token_data.get('symbol', 'UNKNOWN'),
                    'decimals': int(token_data.get('decimals', 18)),
                    'total_supply': float(token_data.get('totalSupply', 0))
                }
                
                # Cache the token info
                self.tx_cache[cache_key] = token_info
                
                return token_info
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {str(e)}")
            return None
    
    async def _process_transactions(self, transactions: List[Dict[str, Any]], address: str) -> None:
        """Process and store transactions"""
        if not self.db or not transactions:
            return
        
        # Filter out transactions we've already processed
        new_transactions = []
        for tx in transactions:
            tx_hash = tx.get('tx_hash')
            
            # Check if we've already processed this transaction
            check_query = f"SELECT tx_hash FROM whale_transactions WHERE tx_hash = '{tx_hash}';"
            result = await self.db.raw_query(check_query)
            
            if not result or not result.get('rows') or len(result['rows']) == 0:
                new_transactions.append(tx)
        
        if not new_transactions:
            logger.debug(f"No new transactions for address {address}")
            return
        
        logger.info(f"Processing {len(new_transactions)} new transactions for {address}")
        
        # Store the new transactions
        values = []
        for tx in new_transactions:
            # Get USD value for the transaction if available
            amount_usd = await self._get_transaction_value_usd(tx)
            tx_type = self._get_transaction_type(tx)
            
            # Add the USD value and transaction type
            tx['amount_usd'] = amount_usd
            tx['tx_type'] = tx_type
            
            # Format the transaction for insertion
            values.append(f"""(
                '{tx['tx_hash']}',
                {tx['block_number']},
                '{tx['from_address']}',
                '{tx['to_address']}',
                {f"'{tx['token_address']}'" if tx['token_address'] else 'NULL'},
                {f"'{tx['token_symbol']}'" if tx['token_symbol'] else 'NULL'},
                {tx.get('value', 0)},
                {amount_usd or 'NULL'},
                '{tx['timestamp'].isoformat()}',
                '{tx['chain_id']}',
                '{tx_type}'
            )""")
        
        if values:
            values_str = ', '.join(values)
            insert_query = f"""
            INSERT INTO whale_transactions (
                tx_hash,
                block_number,
                from_address,
                to_address,
                token_address,
                token_symbol,
                amount,
                amount_usd,
                timestamp,
                chain_id,
                tx_type
            )
            VALUES {values_str}
            ON CONFLICT (tx_hash) DO NOTHING;
            """
            
            await self.db.raw_query(insert_query)
            
            # Analyze these transactions for sentiment
            if self.crypto_panic:
                sentiment = await self._analyze_transaction_sentiment(new_transactions)
                logger.info(f"Transaction sentiment analysis: {sentiment}")
    
    async def _get_transaction_value_usd(self, transaction: Dict[str, Any]) -> Optional[float]:
        """Get the USD value of a transaction"""
        # Implementation would typically call a price API
        # This is a simplified placeholder implementation
        if transaction.get('token_symbol') == 'SONIC':
            # Example: Get SONIC price
            return transaction.get('value', 0) * 0.53  # Sample SONIC price
        elif transaction.get('token_symbol') == 'WETH':
            # Example: Get WETH price
            return transaction.get('value', 0) * 3000  # Sample ETH price
        else:
            # For other tokens, we'd need to lookup their prices
            return None
    
    def _get_transaction_type(self, transaction: Dict[str, Any]) -> str:
        """Determine the type of transaction"""
        from_addr = transaction.get('from_address', '').lower()
        to_addr = transaction.get('to_address', '').lower()
        
        if from_addr in self.monitored_addresses and to_addr in self.monitored_addresses:
            return 'internal_transfer'
        elif from_addr in self.monitored_addresses:
            return 'outgoing'
        elif to_addr in self.monitored_addresses:
            return 'incoming'
        else:
            return 'unknown'
    
    async def _analyze_transaction_sentiment(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the sentiment of transactions"""
        if not self.crypto_panic or len(transactions) == 0:
            return {'sentiment': 'neutral', 'confidence': 0.5}
        
        # Get market sentiment from CryptoPanic
        market_sentiment = await self.crypto_panic.get_market_sentiment()
        
        # Calculate transaction volume metrics
        total_volume = sum(tx.get('amount_usd', 0) or 0 for tx in transactions)
        incoming_volume = sum(tx.get('amount_usd', 0) or 0 for tx in transactions if tx.get('tx_type') == 'incoming')
        outgoing_volume = sum(tx.get('amount_usd', 0) or 0 for tx in transactions if tx.get('tx_type') == 'outgoing')
        
        # Determine flow sentiment
        flow_ratio = incoming_volume / outgoing_volume if outgoing_volume > 0 else float('inf')
        
        if flow_ratio > 1.5:
            flow_sentiment = 'bullish'
            flow_confidence = min(0.5 + (flow_ratio - 1.5) / 10, 0.9)
        elif flow_ratio < 0.67:
            flow_sentiment = 'bearish'
            flow_confidence = min(0.5 + (0.67 - flow_ratio) / 2, 0.9)
        else:
            flow_sentiment = 'neutral'
            flow_confidence = 0.5
        
        # Combine with market sentiment
        market_weight = 0.7
        flow_weight = 0.3
        
        if market_sentiment.get('sentiment') == flow_sentiment:
            combined_sentiment = market_sentiment.get('sentiment')
            combined_confidence = (market_sentiment.get('confidence', 0.5) * market_weight + 
                                flow_confidence * flow_weight)
        else:
            # If sentiments conflict, go with the stronger one
            if market_sentiment.get('confidence', 0.5) > flow_confidence:
                combined_sentiment = market_sentiment.get('sentiment')
                combined_confidence = market_sentiment.get('confidence', 0.5)
            else:
                combined_sentiment = flow_sentiment
                combined_confidence = flow_confidence
        
        return {
            'sentiment': combined_sentiment,
            'confidence': combined_confidence,
            'market_sentiment': market_sentiment.get('sentiment'),
            'flow_sentiment': flow_sentiment,
            'incoming_volume': incoming_volume,
            'outgoing_volume': outgoing_volume,
            'flow_ratio': flow_ratio
        }
    
    async def _update_wallet_balances(self, address: str) -> None:
        """Update wallet balances for a specific address"""
        if not self.db or not self.session:
            return
        
        try:
            # Get balances for the address
            balances = await self._get_wallet_balances(address)
            
            if not balances:
                logger.debug(f"No balance data available for {address}")
                return
            
            # Store the balances
            values = []
            for balance in balances:
                token_address = balance.get('token_address', '').lower()
                token_symbol = balance.get('token_symbol', 'UNKNOWN')
                amount = balance.get('amount', 0)
                amount_usd = balance.get('amount_usd')
                
                values.append(f"""(
                    '{address}',
                    {f"'{token_address}'" if token_address else 'NULL'},
                    '{token_symbol}',
                    {amount},
                    {amount_usd if amount_usd is not None else 'NULL'},
                    CURRENT_TIMESTAMP
                )""")
            
            if values:
                values_str = ', '.join(values)
                upsert_query = f"""
                INSERT INTO whale_balances (
                    address,
                    token_address,
                    token_symbol,
                    amount,
                    amount_usd,
                    updated_at
                )
                VALUES {values_str}
                ON CONFLICT (address, token_address) DO UPDATE SET
                    amount = EXCLUDED.amount,
                    amount_usd = EXCLUDED.amount_usd,
                    updated_at = CURRENT_TIMESTAMP;
                """
                
                await self.db.raw_query(upsert_query)
        except Exception as e:
            logger.error(f"Error updating wallet balances for {address}: {str(e)}")
    
    async def _get_wallet_balances(self, address: str) -> List[Dict[str, Any]]:
        """Get token balances for a specific wallet address"""
        if not self.session:
            return []
        
        # Different endpoints for different chains
        chain_id = 'sonic'  # Default to Sonic chain
        
        if chain_id == 'sonic':
            url = f"https://explorer-api.sonicscan.org/api?module=account&action=tokenlist&address={address}"
        elif chain_id in ('ethereum', 'eth'):
            url = f"https://api.etherscan.io/api?module=account&action=tokenlist&address={address}&apikey={self.config.get('etherscan_key', '')}"
        else:
            logger.warning(f"Unsupported chain ID for balance fetching: {chain_id}")
            return []
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching balances for {address}: HTTP {response.status}")
                    return []
                
                data = await response.json()
                
                if data.get('status') != '1' and data.get('message') != 'OK':
                    logger.error(f"API error for balances {address}: {data.get('message')}")
                    return []
                
                # Extract and format balances
                balances = []
                for token in data.get('result', []):
                    # Skip zero balances
                    if float(token.get('balance', 0)) == 0:
                        continue
                    
                    # Get token details
                    token_info = await self._get_token_info(token.get('contractAddress'), chain_id)
                    
                    # Calculate actual amount based on decimals
                    decimals = int(token.get('decimals', 18))
                    raw_amount = float(token.get('balance', 0))
                    amount = raw_amount / (10 ** decimals)
                    
                    # Get USD value if available
                    amount_usd = await self._get_token_value_usd(
                        token.get('contractAddress'),
                        token.get('symbol'),
                        amount,
                        chain_id
                    )
                    
                    balance = {
                        'token_address': token.get('contractAddress', '').lower(),
                        'token_symbol': token.get('symbol', 'UNKNOWN'),
                        'amount': amount,
                        'amount_usd': amount_usd
                    }
                    
                    balances.append(balance)
                
                # Also add the native token (ETH/SONIC) balance
                native_balance = await self._get_native_balance(address, chain_id)
                if native_balance and native_balance.get('amount', 0) > 0:
                    balances.append(native_balance)
                
                return balances
        except Exception as e:
            logger.error(f"Error getting balances for {address}: {str(e)}")
            return []
    
    async def _get_native_balance(self, address: str, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get the native token balance for an address"""
        if not self.session:
            return None
        
        # Different endpoints for different chains
        if chain_id == 'sonic':
            url = f"https://explorer-api.sonicscan.org/api?module=account&action=balance&address={address}"
            token_symbol = 'SONIC'
        elif chain_id in ('ethereum', 'eth'):
            url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&apikey={self.config.get('etherscan_key', '')}"
            token_symbol = 'ETH'
        else:
            logger.warning(f"Unsupported chain ID for native balance: {chain_id}")
            return None
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching native balance for {address}: HTTP {response.status}")
                    return None
                
                data = await response.json()
                
                if data.get('status') != '1' and data.get('message') != 'OK':
                    logger.error(f"API error for native balance {address}: {data.get('message')}")
                    return None
                
                # Calculate balance
                raw_balance = float(data.get('result', 0))
                balance = raw_balance / 1e18  # Convert to ETH/SONIC
                
                # Get USD value
                amount_usd = await self._get_token_value_usd(None, token_symbol, balance, chain_id)
                
                return {
                    'token_address': None,
                    'token_symbol': token_symbol,
                    'amount': balance,
                    'amount_usd': amount_usd
                }
        except Exception as e:
            logger.error(f"Error getting native balance for {address}: {str(e)}")
            return None
    
    async def _get_token_value_usd(self, token_address: Optional[str], token_symbol: str, amount: float, chain_id: str) -> Optional[float]:
        """Get the USD value of a token amount"""
        # Implementation would typically call a price API
        # This is a simplified placeholder implementation
        if token_symbol == 'SONIC':
            return amount * 0.53  # Sample SONIC price
        elif token_symbol == 'ETH' or token_symbol == 'WETH':
            return amount * 3000  # Sample ETH price
        elif token_symbol == 'USDC' or token_symbol == 'USDT' or token_symbol == 'DAI':
            return amount  # Stablecoins are approximately $1
        else:
            # For other tokens, we'd need to lookup their prices
            return None
    
    async def _analyze_whale_patterns(self) -> None:
        """Analyze patterns in whale activity"""
        if not self.db:
            return
        
        logger.info("Analyzing whale patterns")
        
        try:
            # Get recent transactions (last 24 hours)
            time_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            query = f"""
            SELECT * FROM whale_transactions
            WHERE timestamp > '{time_cutoff}'
            ORDER BY timestamp DESC;
            """
            
            result = await self.db.raw_query(query)
            
            if not result or not result.get('rows'):
                logger.debug("No recent transactions for pattern analysis")
                return
            
            transactions = result['rows']
            
            # Get total transaction volume
            total_volume = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions)
            
            # Get net flow (inflows - outflows)
            outflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                          if tx.get('tx_type') == 'outgoing')
            inflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                         if tx.get('tx_type') == 'incoming')
            net_flow = inflows - outflows
            
            # Get unique active wallets
            active_wallets = set()
            for tx in transactions:
                if tx.get('from_address') in self.monitored_addresses:
                    active_wallets.add(tx.get('from_address'))
                if tx.get('to_address') in self.monitored_addresses:
                    active_wallets.add(tx.get('to_address'))
            
            logger.info(f"""Whale activity summary:
            - Total volume: ${total_volume:,.2f}
            - Net flow: ${net_flow:,.2f} ({'inflows' if net_flow > 0 else 'outflows'})
            - Active wallets: {len(active_wallets)} / {len(self.monitored_addresses)}
            """)
            
            # Analyze transaction patterns for each active wallet
            for wallet in active_wallets:
                await self._analyze_wallet_patterns(wallet)
            
            # Get sentiment analysis
            if self.huggingface:
                combined_text = f"""
                Whale wallets have shown {total_volume:,.2f} USD in transaction volume in the last 24 hours.
                The net flow was {net_flow:,.2f} USD ({'inflows' if net_flow > 0 else 'outflows'}).
                {len(active_wallets)} out of {len(self.monitored_addresses)} monitored wallets were active.
                """
                
                sentiment = await self.huggingface.analyze_sentiment(combined_text)
                logger.info(f"Whale activity sentiment: {sentiment}")
        except Exception as e:
            logger.error(f"Error analyzing whale patterns: {str(e)}")
    
    async def _analyze_wallet_patterns(self, address: str) -> None:
        """Analyze transaction patterns for a specific wallet"""
        if not self.db:
            return
        
        try:
            # Get recent transactions for this wallet
            time_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            query = f"""
            SELECT * FROM whale_transactions
            WHERE (from_address = '{address}' OR to_address = '{address}')
            AND timestamp > '{time_cutoff}'
            ORDER BY timestamp DESC;
            """
            
            result = await self.db.raw_query(query)
            
            if not result or not result.get('rows'):
                logger.debug(f"No recent transactions for wallet {address}")
                return
            
            transactions = result['rows']
            
            # Calculate wallet-specific metrics
            outgoing_txs = [tx for tx in transactions if tx.get('from_address') == address]
            incoming_txs = [tx for tx in transactions if tx.get('to_address') == address]
            
            outgoing_volume = sum(float(tx.get('amount_usd', 0) or 0) for tx in outgoing_txs)
            incoming_volume = sum(float(tx.get('amount_usd', 0) or 0) for tx in incoming_txs)
            
            net_flow = incoming_volume - outgoing_volume
            
            # Get token distribution
            token_distribution = {}
            for tx in transactions:
                token = tx.get('token_symbol', 'Unknown')
                if token not in token_distribution:
                    token_distribution[token] = 0
                
                if tx.get('to_address') == address:
                    token_distribution[token] += float(tx.get('amount', 0) or 0)
                else:
                    token_distribution[token] -= float(tx.get('amount', 0) or 0)
            
            # Log the wallet activity
            if abs(net_flow) > self.whale_threshold:
                action = 'accumulating' if net_flow > 0 else 'distributing'
                logger.info(f"""Whale wallet {address} activity:
                - Action: {action.upper()}
                - Net flow: ${net_flow:,.2f}
                - Outgoing: ${outgoing_volume:,.2f} ({len(outgoing_txs)} txs)
                - Incoming: ${incoming_volume:,.2f} ({len(incoming_txs)} txs)
                - Tokens: {token_distribution}
                """)
        except Exception as e:
            logger.error(f"Error analyzing wallet {address}: {str(e)}")
    
    async def get_transaction_patterns(self) -> Dict[str, Any]:
        """Get transaction patterns for API consumption"""
        if not self.db:
            return {"error": "Database not available"}
        
        try:
            # Get recent transactions (last 24 hours)
            time_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            query = f"""
            SELECT * FROM whale_transactions
            WHERE timestamp > '{time_cutoff}'
            ORDER BY timestamp DESC;
            """
            
            result = await self.db.raw_query(query)
            
            if not result or not result.get('rows'):
                return {"transactions": [], "patterns": {"total_volume": 0, "net_flow": 0, "active_wallets": 0}}
            
            transactions = result['rows']
            
            # Extract and format transactions
            formatted_txs = []
            for tx in transactions:
                formatted_txs.append({
                    "tx_hash": tx.get('tx_hash'),
                    "from": tx.get('from_address'),
                    "to": tx.get('to_address'),
                    "token": tx.get('token_symbol', 'Unknown'),
                    "amount": float(tx.get('amount', 0)),
                    "value_usd": float(tx.get('amount_usd', 0) or 0),
                    "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp'),
                    "type": tx.get('tx_type')
                })
            
            # Calculate patterns
            total_volume = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions)
            outflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                          if tx.get('tx_type') == 'outgoing')
            inflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                         if tx.get('tx_type') == 'incoming')
            net_flow = inflows - outflows
            
            # Get unique active wallets
            active_wallets = set()
            for tx in transactions:
                if tx.get('from_address') in self.monitored_addresses:
                    active_wallets.add(tx.get('from_address'))
                if tx.get('to_address') in self.monitored_addresses:
                    active_wallets.add(tx.get('to_address'))
            
            return {
                "transactions": formatted_txs,
                "patterns": {
                    "total_volume": total_volume,
                    "net_flow": net_flow,
                    "active_wallets": len(active_wallets),
                    "total_wallets": len(self.monitored_addresses),
                    "time_period": "24h"
                }
            }
        except Exception as e:
            logger.error(f"Error getting transaction patterns: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_whale_activity(self, token: Optional[str] = None, chain: str = 'sonic') -> Dict[str, Any]:
        """Analyze whale activity for a specific token or chain"""
        if not self.db:
            return {"error": "Database not available"}
        
        try:
            # Define the time period
            time_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            
            # Base query
            query = f"""
            SELECT * FROM whale_transactions
            WHERE timestamp > '{time_cutoff}'
            """
            
            # Add token filter if specified
            if token:
                query += f" AND token_symbol = '{token.upper()}'"
            
            # Add chain filter
            query += f" AND chain_id = '{chain}'"
            
            # Sort by timestamp
            query += " ORDER BY timestamp DESC;"
            
            result = await self.db.raw_query(query)
            
            if not result or not result.get('rows'):
                return {
                    "token": token.upper() if token else "All tokens",
                    "chain": chain,
                    "time_period": "24h",
                    "transactions": [],
                    "wallets": [],
                    "stats": {
                        "total_volume": 0,
                        "net_flow": 0,
                        "active_wallets": 0
                    }
                }
            
            transactions = result['rows']
            
            # Calculate stats
            total_volume = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions)
            outflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                          if tx.get('tx_type') == 'outgoing')
            inflows = sum(float(tx.get('amount_usd', 0) or 0) for tx in transactions 
                         if tx.get('tx_type') == 'incoming')
            net_flow = inflows - outflows
            
            # Get wallet activity
            wallet_activity = {}
            
            for tx in transactions:
                # Process outgoing transactions (wallet is selling/sending)
                if tx.get('from_address') in self.monitored_addresses:
                    addr = tx.get('from_address')
                    if addr not in wallet_activity:
                        wallet_activity[addr] = {
                            "address": addr,
                            "outgoing_volume": 0,
                            "incoming_volume": 0,
                            "net_flow": 0,
                            "transactions": []
                        }
                    
                    # Update outgoing volume
                    amount_usd = float(tx.get('amount_usd', 0) or 0)
                    wallet_activity[addr]["outgoing_volume"] += amount_usd
                    wallet_activity[addr]["net_flow"] -= amount_usd
                    
                    # Add transaction to wallet's list
                    wallet_activity[addr]["transactions"].append({
                        "tx_hash": tx.get('tx_hash'),
                        "type": "outgoing",
                        "token": tx.get('token_symbol', 'Unknown'),
                        "amount": float(tx.get('amount', 0)),
                        "value_usd": amount_usd,
                        "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp')
                    })
                
                # Process incoming transactions (wallet is buying/receiving)
                if tx.get('to_address') in self.monitored_addresses:
                    addr = tx.get('to_address')
                    if addr not in wallet_activity:
                        wallet_activity[addr] = {
                            "address": addr,
                            "outgoing_volume": 0,
                            "incoming_volume": 0,
                            "net_flow": 0,
                            "transactions": []
                        }
                    
                    # Update incoming volume
                    amount_usd = float(tx.get('amount_usd', 0) or 0)
                    wallet_activity[addr]["incoming_volume"] += amount_usd
                    wallet_activity[addr]["net_flow"] += amount_usd
                    
                    # Add transaction to wallet's list
                    wallet_activity[addr]["transactions"].append({
                        "tx_hash": tx.get('tx_hash'),
                        "type": "incoming",
                        "token": tx.get('token_symbol', 'Unknown'),
                        "amount": float(tx.get('amount', 0)),
                        "value_usd": amount_usd,
                        "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp')
                    })
            
            # Sort and categorize wallets
            active_wallets = []
            for addr, data in wallet_activity.items():
                # Determine action based on net flow
                if data["net_flow"] > self.whale_threshold:
                    action = "accumulating"
                elif data["net_flow"] < -self.whale_threshold:
                    action = "distributing"
                else:
                    action = "neutral"
                
                # Add action and sort transactions
                data["action"] = action
                data["transactions"].sort(key=lambda tx: tx["timestamp"], reverse=True)
                
                # Calculate volume
                data["volume"] = data["incoming_volume"] + data["outgoing_volume"]
                
                active_wallets.append(data)
            
            # Sort wallets by total volume
            active_wallets.sort(key=lambda w: w["volume"], reverse=True)
            
            # Prepare formatted transactions
            formatted_txs = []
            for tx in transactions:
                formatted_txs.append({
                    "tx_hash": tx.get('tx_hash'),
                    "from": tx.get('from_address'),
                    "to": tx.get('to_address'),
                    "token": tx.get('token_symbol', 'Unknown'),
                    "amount": float(tx.get('amount', 0)),
                    "value_usd": float(tx.get('amount_usd', 0) or 0),
                    "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp')
                })
            
            # Return the analysis
            return {
                "token": token.upper() if token else "All tokens",
                "chain": chain,
                "time_period": "24h",
                "transactions": formatted_txs,
                "wallets": active_wallets,
                "stats": {
                    "total_volume": total_volume,
                    "net_flow": net_flow,
                    "active_wallets": len(wallet_activity)
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing whale activity: {str(e)}")
            return {"error": str(e)}
    
    async def get_wallet_summary(self, address: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of wallet's activity and holdings"""
        if not self.db:
            return {"error": "Database not available"}
            
        # Normalize address
        address = address.lower()
        
        try:
            # Check if this is a monitored wallet
            is_whale = address in self.monitored_addresses
            
            # Get wallet's token balances
            balances_query = f"""
            SELECT * FROM whale_balances
            WHERE address = '{address}'
            """
            
            if token:
                balances_query += f" AND token_symbol = '{token.upper()}'"
                
            balances_query += " ORDER BY amount_usd DESC NULLS LAST;"
            
            balances_result = await self.db.raw_query(balances_query)
            
            # Get wallet's recent transactions
            time_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            txs_query = f"""
            SELECT * FROM whale_transactions
            WHERE (from_address = '{address}' OR to_address = '{address}')
            AND timestamp > '{time_cutoff}'
            """
            
            if token:
                txs_query += f" AND token_symbol = '{token.upper()}'"
                
            txs_query += " ORDER BY timestamp DESC LIMIT 50;"
            
            txs_result = await self.db.raw_query(txs_query)
            
            # Format balances
            formatted_balances = []
            total_value = 0
            
            if balances_result and balances_result.get('rows'):
                for balance in balances_result['rows']:
                    value_usd = float(balance.get('amount_usd', 0) or 0)
                    total_value += value_usd
                    
                    formatted_balances.append({
                        "token": balance.get('token_symbol', 'Unknown'),
                        "amount": float(balance.get('amount', 0)),
                        "value_usd": value_usd,
                        "updated_at": balance.get('updated_at').isoformat() if hasattr(balance.get('updated_at'), 'isoformat') else balance.get('updated_at')
                    })
            
            # Format transactions
            formatted_txs = []
            
            if txs_result and txs_result.get('rows'):
                for tx in txs_result['rows']:
                    # Determine direction
                    if tx.get('from_address') == address:
                        direction = "outgoing"
                    else:
                        direction = "incoming"
                    
                    formatted_txs.append({
                        "tx_hash": tx.get('tx_hash'),
                        "type": direction,
                        "token": tx.get('token_symbol', 'Unknown'),
                        "amount": float(tx.get('amount', 0)),
                        "value_usd": float(tx.get('amount_usd', 0) or 0),
                        "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp'),
                        "counterparty": tx.get('to_address') if direction == "outgoing" else tx.get('from_address')
                    })
            
            # Get transaction stats
            outgoing_volume = sum(tx["value_usd"] for tx in formatted_txs if tx["type"] == "outgoing")
            incoming_volume = sum(tx["value_usd"] for tx in formatted_txs if tx["type"] == "incoming")
            net_flow = incoming_volume - outgoing_volume
            
            # Return the wallet summary
            return {
                "address": address,
                "is_whale": is_whale,
                "balances": formatted_balances,
                "total_value_usd": total_value,
                "recent_transactions": formatted_txs,
                "stats": {
                    "outgoing_volume": outgoing_volume,
                    "incoming_volume": incoming_volume,
                    "net_flow": net_flow,
                    "transaction_count": len(formatted_txs)
                }
            }
        except Exception as e:
            logger.error(f"Error getting wallet summary for {address}: {str(e)}")
            return {"error": str(e)}
    
    async def get_transaction_details(self, tx_hash: str) -> Dict[str, Any]:
        """Get detailed information about a specific transaction"""
        if not self.db:
            return {"error": "Database not available"}
        
        try:
            # Query the transaction from the database
            query = f"SELECT * FROM whale_transactions WHERE tx_hash = '{tx_hash}';"
            result = await self.db.raw_query(query)
            
            if not result or not result.get('rows') or len(result['rows']) == 0:
                # Transaction not in our database, try to fetch it from explorer API
                return await self._fetch_transaction_details(tx_hash)
            
            # Format the transaction details
            tx = result['rows'][0]
            
            return {
                "tx_hash": tx.get('tx_hash'),
                "block": tx.get('block_number'),
                "from": tx.get('from_address'),
                "to": tx.get('to_address'),
                "token": tx.get('token_symbol', 'Unknown'),
                "value": float(tx.get('amount', 0)),
                "value_usd": float(tx.get('amount_usd', 0) or 0),
                "timestamp": tx.get('timestamp').isoformat() if hasattr(tx.get('timestamp'), 'isoformat') else tx.get('timestamp'),
                "chain_id": tx.get('chain_id'),
                "type": tx.get('tx_type'),
                "gas_used": tx.get('gas_used', 0),
                "gas_price": tx.get('gas_price', 0)
            }
        except Exception as e:
            logger.error(f"Error getting transaction details for {tx_hash}: {str(e)}")
            return {"error": str(e)}
    
    async def _fetch_transaction_details(self, tx_hash: str) -> Dict[str, Any]:
        """Fetch transaction details from explorer API"""
        if not self.session:
            return {"error": "Session not available"}
        
        # Default to Sonic chain
        chain_id = 'sonic'
        
        # Different endpoints for different chains
        if chain_id == 'sonic':
            url = f"https://explorer-api.sonicscan.org/api?module=transaction&action=gettxinfo&txhash={tx_hash}"
        elif chain_id in ('ethereum', 'eth'):
            url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={self.config.get('etherscan_key', '')}"
        else:
            return {"error": f"Unsupported chain ID: {chain_id}"}
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP error: {response.status}"}
                
                data = await response.json()
                
                if data.get('status') != '1' and data.get('message') != 'OK':
                    return {"error": f"API error: {data.get('message')}"}
                
                # Extract transaction details
                tx_data = data.get('result', {})
                
                # Format may vary by chain, this is for Sonic
                tx = {
                    "tx_hash": tx_hash,
                    "block": int(tx_data.get('blockNumber', 0), 16) if isinstance(tx_data.get('blockNumber'), str) and tx_data.get('blockNumber', '').startswith('0x') else int(tx_data.get('blockNumber', 0)),
                    "from": tx_data.get('from', '').lower(),
                    "to": tx_data.get('to', '').lower(),
                    "value": float(int(tx_data.get('value', 0), 16) / 1e18) if isinstance(tx_data.get('value'), str) and tx_data.get('value', '').startswith('0x') else float(tx_data.get('value', 0)) / 1e18,
                    "timestamp": tx_data.get('timeStamp'),
                    "chain_id": chain_id,
                    "gas_used": int(tx_data.get('gasUsed', 0), 16) if isinstance(tx_data.get('gasUsed'), str) and tx_data.get('gasUsed', '').startswith('0x') else int(tx_data.get('gasUsed', 0)),
                    "gas_price": float(int(tx_data.get('gasPrice', 0), 16) / 1e9) if isinstance(tx_data.get('gasPrice'), str) and tx_data.get('gasPrice', '').startswith('0x') else float(tx_data.get('gasPrice', 0)) / 1e9
                }
                
                # Determine if this is a token transfer
                input_data = tx_data.get('input', '')
                if input_data and input_data.startswith('0xa9059cbb'):  # ERC20 transfer method signature
                    # This is a token transfer, try to extract token details
                    contract_address = tx_data.get('to', '')
                    token_info = await self._get_token_info(contract_address, chain_id)
                    
                    if token_info:
                        tx['token'] = token_info.get('symbol', 'Unknown')
                        
                        # Try to parse the transfer amount from input data
                        if len(input_data) >= 138:  # Length of a standard ERC20 transfer
                            try:
                                # Extract to_address (bytes 10-74)
                                to_addr = '0x' + input_data[34:74].lower()
                                tx['to'] = to_addr
                                
                                # Extract amount (bytes 74-138)
                                amount_hex = input_data[74:138]
                                amount = int(amount_hex, 16) / (10 ** token_info.get('decimals', 18))
                                tx['value'] = amount
                            except Exception as e:
                                logger.error(f"Error parsing token transfer data: {str(e)}")
                else:
                    # Native token transfer
                    tx['token'] = 'SONIC' if chain_id == 'sonic' else 'ETH'
                
                # Try to get USD value
                tx['value_usd'] = await self._get_token_value_usd(
                    None if tx.get('token') in ('SONIC', 'ETH') else tx_data.get('to'),
                    tx.get('token', 'Unknown'),
                    tx.get('value', 0),
                    chain_id
                )
                
                # Determine transaction type
                if tx.get('from') in self.monitored_addresses and tx.get('to') in self.monitored_addresses:
                    tx['type'] = 'internal_transfer'
                elif tx.get('from') in self.monitored_addresses:
                    tx['type'] = 'outgoing'
                elif tx.get('to') in self.monitored_addresses:
                    tx['type'] = 'incoming'
                else:
                    tx['type'] = 'unknown'
                
                return tx
        except Exception as e:
            logger.error(f"Error fetching transaction details for {tx_hash}: {str(e)}")
            return {"error": str(e)}
    
    async def add_whale_address(self, address: str, label: Optional[str] = None) -> bool:
        """Add a new whale address to monitoring"""
        if not self.db or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return False
        
        try:
            # Add the address to the database
            address = address.lower()
            label = label or 'Tracked Whale'
            
            query = f"""
            INSERT INTO whale_addresses (address, label, tags)
            VALUES ('{address}', '{label}', ARRAY['whale'])
            ON CONFLICT (address) DO UPDATE SET
                label = '{label}',
                tags = ARRAY['whale'];
            """
            
            await self.db.raw_query(query)
            
            # Add to the monitored addresses set
            self.monitored_addresses.add(address)
            
            logger.info(f"Added whale address {address} with label '{label}'")
            return True
        except Exception as e:
            logger.error(f"Error adding whale address {address}: {str(e)}")
            return False
    
    async def remove_whale_address(self, address: str) -> bool:
        """Remove a whale address from monitoring"""
        if not self.db:
            return False
        
        try:
            # Remove the address from the database
            address = address.lower()
            query = f"DELETE FROM whale_addresses WHERE address = '{address}';"
            await self.db.raw_query(query)
            
            # Remove from the monitored addresses set
            if address in self.monitored_addresses:
                self.monitored_addresses.remove(address)
            
            logger.info(f"Removed whale address {address}")
            return True
        except Exception as e:
            logger.error(f"Error removing whale address {address}: {str(e)}")
            return False
    
    async def get_whale_summary(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of whale activity"""
        # We'll reuse the analyze_whale_activity method
        return await self.analyze_whale_activity(token)
    
    async def process_telegram_commands(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegram commands related to whale tracking"""
        command = command.lower()
        
        if command == 'whale':
            # Handle whale command
            address = params.get('address')
            token = params.get('token')
            
            if address:
                return await self.get_wallet_summary(address, token)
            else:
                return await self.get_whale_summary(token)
        elif command == 'tx' or command == 'transaction':
            # Handle transaction command
            tx_hash = params.get('tx_hash')
            
            if not tx_hash:
                return {"error": "Transaction hash required"}
            
            return await self.get_transaction_details(tx_hash)
        elif command == 'add_whale':
            # Handle add whale command
            address = params.get('address')
            label = params.get('label')
            
            if not address:
                return {"error": "Address required"}
            
            success = await self.add_whale_address(address, label)
            
            if success:
                return {"success": True, "message": f"Added whale address {address}"}
            else:
                return {"error": f"Failed to add whale address {address}"}
        else:
            return {"error": f"Unknown whale command: {command}"}
    
    async def notify_large_movements(self, threshold: float = 100000.0) -> None:
        """Notify about large whale movements"""
        # This would typically send notifications to TelegramService, Discord, etc.
        # Simple stub for integration with other services
        pass
    
    async def close(self) -> None:
        """Close connections and cleanup resources"""
        self.running = False
        
        if self.crypto_panic:
            await self.crypto_panic.close()
        
        if self.session:
            await self.session.close()
            
        logger.info("Whale tracker service shut down")


async def test_whale_tracker():
    """Test the whale tracker service"""
    from ..server.db import Database
    from ..services.cryptopanic_service import CryptoPanicService
    
    # Create database connection
    db = Database()
    if not await db.is_connected():
        await db.connect()
    
    # Create cryptopanic service
    crypto_panic = CryptoPanicService({
        'api_key': 'your_cryptopanic_api_key'  # Replace with your key
    })
    
    # Create and initialize whale tracker
    tracker = WhaleTrackerService({
        'db': db,
        'crypto_panic': crypto_panic,
        'update_interval': 300,  # 5 minutes for testing
        'whale_threshold': 50000  # $50k USD for testing
    })
    
    await tracker.initialize()
    
    # Get whale summary
    summary = await tracker.get_whale_summary()
    print(f"Whale Summary: {json.dumps(summary, indent=2)}")
    
    # Get specific wallet
    wallet = await tracker.get_wallet_summary("0xAdDbD648c380E4822e9c934B0fc5C9f607d892c5")
    print(f"Wallet Details: {json.dumps(wallet, indent=2)}")
    
    # Clean up
    await tracker.close()
    await db.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_whale_tracker())