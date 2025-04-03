import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from typing import Optional, Union, Dict, List
import pandas as pd
import io
import requests
import json
import psycopg2
from datetime import datetime
from datasets import load_dataset

logger = logging.getLogger(__name__)

class SupabaseConnection:
    def __init__(self):
        """Initialize Supabase connection using environment variables."""
        load_dotenv()
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        # Use only environment variable for database connection
        self.pg_url = os.getenv("DATABASE_URL")

        if not self.url or not self.key:
            raise ValueError("Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")

        if not self.pg_url:
            raise ValueError("Missing DATABASE_URL environment variable")

        self.client = None
        self.pg_conn = None
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def connect(self) -> Client:
        """Create and return a Supabase client instance."""
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Successfully connected to Supabase")
            return self.client
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            raise

    def connect_pg(self):
        """Connect to PostgreSQL using connection pooling."""
        try:
            if not self.pg_conn or self.pg_conn.closed:
                self.pg_conn = psycopg2.connect(
                    self.pg_url,
                    # Add connection pooling settings
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
                self.pg_conn.set_session(autocommit=False)
                logger.info("Successfully connected to PostgreSQL using pooler")
            return self.pg_conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test the Supabase connection by attempting to fetch data."""
        try:
            if not self.client:
                self.connect()
            response = self.client.storage.list_buckets()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False

    async def store_crypto_data(self, data: List[Dict]) -> bool:
        """Store crypto training data in database using connection pooling."""
        try:
            conn = self.connect_pg()
            cursor = conn.cursor()

            batch_size = 1000
            total_stored = 0

            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                try:
                    for record in batch:
                        cursor.execute("""
                            INSERT INTO crypto_data 
                            (description, financial_info)
                            VALUES (%s, %s)
                        """, (
                            record.get('assistant', ''),
                            json.dumps({
                                'label': record.get('label', ''),
                                'score': record.get('score', 0.0)
                            })
                        ))

                    conn.commit()
                    total_stored += len(batch)
                    logger.info(f"Stored batch of {len(batch)} crypto training records")

                except Exception as batch_error:
                    conn.rollback()
                    logger.error(f"Failed to store batch: {str(batch_error)}")
                    logger.error(f"Batch data sample: {batch[0] if batch else 'No data'}")
                    continue

            if total_stored > 0:
                logger.info(f"Successfully stored total of {total_stored} records")
                return True
            else:
                logger.error("No records were stored successfully")
                return False

        except Exception as e:
            logger.error(f"Failed to store crypto data: {str(e)}")
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn and not conn.closed:
                conn.close()

    async def import_huggingface_dataset(self, dataset_name: str = "Seb0099/crypto-dataset-gpt-4o") -> bool:
        """Import and store data from a Hugging Face dataset."""
        try:
            logger.info(f"Loading dataset: {dataset_name}")
            dataset = load_dataset(dataset_name)

            if not dataset:
                logger.error("Failed to load dataset")
                return False

            logger.info("Successfully loaded dataset, processing records...")

            # Convert dataset to records
            records = []
            for split in dataset.keys():
                for item in dataset[split]:
                    try:
                        # Process the training data - handle fields with leading spaces
                        assistant = item.get(' assistant', '').strip()
                        label = item.get(' label', '').strip()
                        score = float(item.get(' score', 0.0))

                        # Store the processed record
                        record = {
                            'assistant': assistant,
                            'label': label,
                            'score': score
                        }
                        records.append(record)

                        if len(records) % 1000 == 0:
                            logger.info(f"Processed {len(records)} records")
                    except Exception as e:
                        logger.warning(f"Failed to process record: {e}")
                        continue

            # Store the processed records
            if records:
                logger.info(f"Attempting to store {len(records)} processed records")
                success = await self.store_crypto_data(records)
                if success:
                    logger.info(f"Successfully stored {len(records)} records from Hugging Face dataset")
                    return True
                else:
                    logger.error("Failed to store records in database")
                    return False
            else:
                logger.warning("No valid records found in dataset")
                return False

        except Exception as e:
            logger.error(f"Failed to import Hugging Face dataset: {str(e)}")
            return False

    def get_historical_prices(self, symbol: str, start_date: datetime, end_date: datetime, 
                            limit: int = 1000) -> List[Dict]:
        """Retrieve historical price data for a symbol within a date range using connection pooling."""
        try:
            conn = self.connect_pg()
            cursor = conn.cursor()

            # Log the query parameters for debugging
            logger.info(f"Querying historical prices with params: symbol={symbol}, start_date={start_date}, end_date={end_date}, limit={limit}")

            query = """
                SELECT symbol, price, volume, market_cap, timestamp, source
                FROM historical_prices
                WHERE UPPER(symbol) = UPPER(%s)
                AND timestamp >= %s
                AND timestamp <= %s
                ORDER BY timestamp DESC
                LIMIT %s
            """

            cursor.execute(query, (symbol, start_date, end_date, limit))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'symbol': row[0],
                    'price': float(row[1]) if row[1] else 0.0,
                    'volume': float(row[2]) if row[2] else None,
                    'market_cap': float(row[3]) if row[3] else None,
                    'timestamp': row[4].isoformat() if row[4] else None,
                    'source': row[5]
                })

            logger.info(f"Retrieved {len(results)} historical price records for {symbol}")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve historical prices: {str(e)}")
            return []
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn and not conn.closed:
                conn.close()