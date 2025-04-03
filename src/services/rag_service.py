"""RAG service implementation"""
import logging
import traceback
from typing import List, Dict, Any, Optional
import os
from sentence_transformers import SentenceTransformer
import json
import asyncpg
from datetime import datetime

logger = logging.getLogger("services.rag")

class RAGService:
    """Service for Retrieval Augmented Generation"""

    def __init__(self):
        """Initialize RAG service"""
        try:
            self.docs_path = "attached_assets"
            self.documents = []
            self.router_docs = {}  # Cache for router docs

            # Initialize encoder later to avoid loading model until needed
            self.encoder = None
            self.is_initialized = False

            logger.info("RAG service instance created")
        except Exception as e:
            logger.error(f"Error initializing RAG service: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def initialize(self):
        """Initialize the service and load documents"""
        try:
            logger.info("Starting RAG service initialization...")

            # Initialize sentence transformer
            logger.info("Loading sentence transformer model...")
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Sentence transformer model loaded")

            # Load documents from database
            logger.info("Loading documents from database...")
            await self.load_documents()
            logger.info("✅ Documents loaded successfully")

            self.is_initialized = True
            logger.info("✅ RAG service initialization complete")

        except Exception as e:
            logger.error(f"❌ Error during RAG service initialization: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def load_documents(self):
        """Load documents from PostgreSQL"""
        try:
            logger.info("Connecting to database...")
            conn = await asyncpg.connect(os.environ["DATABASE_URL"])
            logger.info("✅ Database connection established")

            # Load router documentation
            logger.info("Loading router documentation...")
            router_docs = await conn.fetch("""
                SELECT * FROM router_documentation 
                ORDER BY created_at DESC
            """)

            for doc in router_docs:
                self.documents.append({
                    "content": doc["content"],
                    "source": "router_docs",
                    "metadata": {
                        "router": doc["router_name"],
                        "type": f"{doc['router_name']}_documentation",
                        "category": doc["category"],
                        "created_at": doc["created_at"].isoformat(),
                        "doc_type": doc["doc_type"]
                    }
                })
            logger.info(f"✅ Loaded {len(router_docs)} router documentation items")

            # Load Twitter data
            logger.info("Loading Twitter data...")
            tweets = await conn.fetch("""
                SELECT * FROM twitter_data 
                ORDER BY created_at DESC 
                LIMIT 100
            """)

            for tweet in tweets:
                self.documents.append({
                    "content": tweet["content"],
                    "source": "twitter",
                    "metadata": {
                        "tweet_id": tweet["tweet_id"],
                        "author": tweet["author"],
                        "sentiment": tweet["sentiment"],
                        "category": tweet["category"],
                        "created_at": tweet["created_at"].isoformat()
                    }
                })
            logger.info(f"✅ Loaded {len(tweets)} tweets")

            # Load local files - this part is kept from the original code.
            if os.path.exists(self.docs_path):
                for filename in os.listdir(self.docs_path):
                    if filename.endswith(".txt"):
                        file_path = os.path.join(self.docs_path, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                self.documents.append({
                                    "content": content,
                                    "source": filename,
                                    "metadata": {
                                        "path": file_path,
                                        "name": filename,
                                        "type": "text",
                                        "storage": "local"
                                    }
                                })
                                logger.info(f"Loaded local document: {filename}")
                        except Exception as e:
                            logger.error(f"Error reading file {filename}: {str(e)}")

            await conn.close()
            logger.info("✅ Database connection closed")

            logger.info(f"Total documents loaded: {len(self.documents)}")

        except Exception as e:
            logger.error(f"❌ Error loading documents: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _encode_text(self, text: str) -> List[float]:
        """Encode text to vector using sentence transformer"""
        if not self.encoder:
            logger.error("Sentence transformer not initialized")
            return []

        try:
            return self.encoder.encode(text).tolist()
        except Exception as e:
            logger.error(f"Error encoding text: {str(e)}")
            return []

    def get_relevant_documents(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Get relevant documents using semantic search"""
        try:
            # Encode query
            query_embedding = self._encode_text(query)
            if not query_embedding:
                return []

            # Calculate similarity scores
            scored_docs = []
            for doc in self.documents:
                doc_embedding = self._encode_text(doc["content"])
                if doc_embedding:
                    # Calculate cosine similarity
                    similarity = sum(a * b for a, b in zip(query_embedding, doc_embedding))
                    similarity /= (sum(a * a for a in query_embedding) ** 0.5)
                    similarity /= (sum(b * b for b in doc_embedding) ** 0.5)
                    scored_docs.append((similarity, doc))

            # Sort by score and return top k
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            return [doc for score, doc in scored_docs[:k]]

        except Exception as e:
            logger.error(f"Error getting relevant documents: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def search_all_content(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all content types with filters"""
        try:
            if not self.is_initialized:
                logger.error("RAG service not initialized")
                return []

            # Get relevant documents
            relevant_docs = self.get_relevant_documents(query, k=limit * 2)

            # Apply filters if provided
            if filters:
                filtered_docs = []
                for doc in relevant_docs:
                    metadata = doc.get('metadata', {})

                    # Check each filter criterion
                    matches = True
                    for key, value in filters.items():
                        if key == 'router':
                            matches = matches and metadata.get('router', '').lower() == value.lower()
                        elif key == 'doc_type':
                            matches = matches and metadata.get('doc_type', '') == value
                        elif key == 'source':
                            matches = matches and metadata.get('source', '') == value

                    if matches:
                        filtered_docs.append(doc)

                relevant_docs = filtered_docs[:limit]

            logger.info(f"Found {len(relevant_docs)} relevant documents for query: {query}")
            return relevant_docs[:limit]

        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def get_router_documentation(self, router_name: str = None) -> List[Dict[str, Any]]:
        """Get router-specific documentation"""
        try:
            # First check router-specific cache
            if router_name and router_name.lower() in self.router_docs:
                logger.info(f"Using cached documentation for router: {router_name}")
                return self.router_docs[router_name.lower()]

            # Filter for router documentation
            docs = []
            logger.info(f"Filtering documents for router: {router_name}")
            logger.debug(f"Total documents available: {len(self.documents)}")

            for doc in self.documents:
                metadata = doc.get('metadata', {})
                router = metadata.get('router', '').lower()
                doc_type = metadata.get('type', '').lower()
                source = metadata.get('source', '').lower()

                # Debug logging
                logger.debug(f"Document metadata - router: {router}, type: {doc_type}, source: {source}")

                if router_name:
                    router_key = router_name.lower()
                    is_matching_doc = (
                        (router == router_key or router_key in doc_type) and
                        (doc_type.endswith('_documentation') or doc_type.endswith('_example') or
                         'router' in doc_type or source.endswith('_docs'))
                    )
                    if is_matching_doc:
                        logger.debug(f"Found {router_name} documentation: {doc.get('title', '')}")
                        docs.append(doc)
                else:
                    is_router_doc = (
                        router or
                        doc_type.endswith('_documentation') or
                        doc_type.endswith('_example') or
                        'router' in doc_type or
                        source.endswith('_docs')
                    )
                    if is_router_doc:
                        docs.append(doc)

            # Cache results if router-specific
            if router_name:
                self.router_docs[router_name.lower()] = docs
                if not docs:
                    logger.warning(f"No documentation found for router: {router_name}")
                else:
                    logger.info(f"Found {len(docs)} documents for router: {router_name}")

            logger.info(f"Retrieved {len(docs)} router documentation items")
            return docs

        except Exception as e:
            logger.error(f"Error retrieving router documentation: {str(e)}")
            return []

    async def store_router_documentation(self, router_name: str, docs: List[Dict[str, Any]]) -> bool:
        """Store router-specific documentation"""
        try:
            stored_count = 0
            for doc in docs:
                try:
                    # Log document metadata before storage
                    logger.debug(f"Storing {router_name} doc with metadata: {doc['metadata']}")

                    # Ensure router field is set in metadata
                    metadata = doc['metadata']
                    if 'router' not in metadata:
                        metadata['router'] = router_name.lower()

                    # This function is removed as it's not used anymore in this revised code.
                    # success = await self.store_document(
                    #     content=f"{doc['title']}\n\n{doc['content']}",
                    #     metadata=metadata
                    # )
                    # if success:
                    #     stored_count += 1
                    #     logger.debug(f"Successfully stored {router_name} documentation: {doc['title']}")
                    pass # Placeholder for removed function.  Storage is handled in the new load_documents


                except Exception as e:
                    logger.error(f"Error storing document {doc.get('title', '')}: {str(e)}")
                    continue

            if stored_count > 0:
                # Clear router cache to force refresh
                self.router_docs.pop(router_name.lower(), None)
                logger.info(f"Successfully stored {stored_count} {router_name} documentation items")
                return True
            return False

        except Exception as e:
            logger.error(f"Error storing {router_name} documentation: {str(e)}")
            return False

    async def validate_router_integration(self, router_name: str, integration_details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate router integration against stored knowledge"""
        try:
            # Get relevant documentation
            docs = await self.get_router_documentation(router_name)
            logger.debug(f"Found {len(docs)} documents for validation of {router_name}")

            if not docs:
                return {
                    "valid": False,
                    "message": f"No documentation found for {router_name}",
                    "details": "Please ensure the router documentation has been ingested into the knowledge base."
                }

            # Check for required fields based on documentation
            required_fields = {
                'odos': ['chainId', 'routerAddress', 'tokens'],
                'kyberswap': ['chainId', 'routerAddress', 'tokens'],
                'all': ['chainId', 'routerAddress']  # Common required fields
            }

            router_key = router_name.lower()
            fields_to_check = required_fields.get(router_key, required_fields['all'])

            missing_fields = [field for field in fields_to_check
                             if field not in integration_details]

            if missing_fields:
                relevant_doc = next((doc for doc in docs
                                   if doc.get('metadata', {}).get('type', '').endswith('_documentation')), None)
                doc_snippet = relevant_doc.get('content', '')[:200] if relevant_doc else ''

                return {
                    "valid": False,
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "documentation": doc_snippet,
                    "available_docs": len(docs)
                }

            # Validate chain ID
            chain_id = integration_details.get('chainId')
            if not isinstance(chain_id, int):
                return {
                    "valid": False,
                    "message": "Chain ID must be an integer",
                    "field": "chainId"
                }

            # Validate router address format
            router_address = integration_details.get('routerAddress', '')
            if not router_address.startswith('0x') or len(router_address) != 42:
                return {
                    "valid": False,
                    "message": "Invalid router address format. Expected 0x-prefixed 40-character hex string",
                    "field": "routerAddress"
                }

            # Validate tokens if required
            if 'tokens' in fields_to_check and not integration_details.get('tokens', []):
                return {
                    "valid": False,
                    "message": "Token list cannot be empty",
                    "field": "tokens"
                }

            # Log successful validation details
            logger.info(f"Successfully validated {router_name} integration with {len(docs)} documentation items")

            return {
                "valid": True,
                "message": "Integration details validated successfully",
                "documentation_count": len(docs),
                "available_examples": len([d for d in docs if d.get('metadata', {}).get('type', '').endswith('_example')])
            }

        except Exception as e:
            logger.error(f"Error validating router integration: {str(e)}")
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }

    #The store_document function is removed because its functionality is now integrated within the load_documents method.

    async def query(self, question: str, k: int = 4) -> Dict[str, Any]:
        """Query the document collection with semantic search"""
        try:
            # Get relevant documents
            relevant_docs = self.get_relevant_documents(question, k)

            if not relevant_docs:
                return {
                    "answer": "No relevant information found.",
                    "sources": []
                }

            # Format sources for response
            sources = []
            for doc in relevant_docs:
                # Include metadata based on storage type
                if doc["metadata"].get("source") == "supabase":
                    source_text = f"[Crypto Analysis {doc['metadata'].get('created_at', 'N/A')}]: {doc['content'][:200]}..."
                    if doc["metadata"].get("financial_info"):
                        source_text += f"\nSignal: {doc['metadata']['financial_info']}"
                elif doc["metadata"].get("source") == "twitter":
                    source_text = f"Twitter @{doc['metadata'].get('author', 'unknown')}: {doc['content'][:200]}..."
                else:
                    source_text = f"{doc['source']}: {doc['content'][:200]}..."
                sources.append(source_text)

            # Generate answer based on document types
            crypto_docs = [d for d in relevant_docs if d["metadata"].get("type") == "crypto_analysis"]
            if crypto_docs:
                answer = f"Found {len(crypto_docs)} relevant crypto analyses. "
                # Add summary of financial information if available
                financial_info = [d["metadata"].get("financial_info") for d in crypto_docs if d["metadata"].get("financial_info")]
                if financial_info:
                    answer += f"Trading signals available for {len(financial_info)} documents."
            else:
                answer = f"Found {len(relevant_docs)} relevant documents from {', '.join(set(d['source'] for d in relevant_docs))}."

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error querying document collection: {str(e)}")
            return {
                "error": str(e),
                "sources": []
            }

    async def store_twitter_data(self, tweets: List[Dict[str, Any]]) -> bool:
        """Store Twitter data in the knowledge base"""
        try:
            success_count = 0
            for tweet in tweets:
                # Format tweet content for storage
                content = f"""
                Tweet: {tweet.get('full_text', '')}
                Author: @{tweet.get('username', 'unknown')}
                Engagement: {tweet.get('likes', 0)} likes, {tweet.get('retweets', 0)} retweets
                Time: {tweet.get('created_at', '')}
                """

                metadata = {
                    **tweet.get('metadata', {}),
                    'tweet_id': tweet.get('id_str'),
                    'author': tweet.get('username'),
                    'engagement_metrics': {
                        'likes': tweet.get('likes', 0),
                        'retweets': tweet.get('retweets', 0),
                        'replies': tweet.get('replies', 0)
                    },
                    'source': 'twitter'
                }

                # This function is removed because storage is handled in the new load_documents method
                # if await self.store_document(content, metadata):
                #     success_count += 1
                pass # Placeholder for removed function

            logger.info(f"Successfully stored {success_count} tweets out of {len(tweets)}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error storing Twitter data: {str(e)}")
            return False

    def get_relevant_tweets(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Get relevant tweets using semantic search"""
        try:
            # Filter for only Twitter documents
            twitter_docs = [
                doc for doc in self.documents
                if doc.get('metadata', {}).get('source') == 'twitter'
            ]

            # Encode query
            query_embedding = self._encode_text(query)

            # Calculate similarity scores for Twitter documents
            scored_docs = []
            for doc in twitter_docs:
                doc_embedding = self._encode_text(doc["content"])

                # Calculate cosine similarity
                if doc_embedding and query_embedding:
                    similarity = sum(a * b for a, b in zip(query_embedding, doc_embedding))
                    similarity /= (sum(a * a for a in query_embedding) ** 0.5)
                    similarity /= (sum(b * b for b in doc_embedding) ** 0.5)
                    scored_docs.append((similarity, doc))

            # Sort by score and return top k
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            return [doc for score, doc in scored_docs[:k]]

        except Exception as e:
            logger.error(f"Error getting relevant tweets: {str(e)}")
            return []

    def get_most_recent_tweet_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get the most recent tweet from a specific username"""
        try:
            # Filter tweets by username
            tweets = [doc for doc in self.documents
                     if doc.get("metadata", {}).get("source") == "twitter"
                     and doc.get("metadata", {}).get("author", "").lower() == username.lower()]

            logger.info(f"Found {len(tweets)} tweets from @{username}")

            if not tweets:
                logger.warning(f"No tweets found for @{username}")
                return None

            # Sort by creation timestamp
            tweets.sort(
                key=lambda d: d["metadata"].get("created_at", ""),
                reverse=True
            )

            most_recent = tweets[0]
            logger.info(f"Retrieved most recent tweet from @{username} posted at {most_recent['metadata'].get('created_at')}")

            return most_recent

        except Exception as e:
            logger.error(f"Error retrieving tweet for {username}: {str(e)}")
            return None

    async def search_all_content(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all content types (documentation and Twitter data)"""
        try:
            # Get relevant documents using semantic search
            relevant_docs = self.get_relevant_documents(query, k=limit * 2)  # Get more docs initially for filtering

            # Apply filters if provided
            if filters:
                filtered_docs = []
                for doc in relevant_docs:
                    metadata = doc.get('metadata', {})

                    # Check each filter criterion
                    matches = True
                    for key, value in filters.items():
                        if key == 'router':
                            matches = matches and metadata.get('router', '').lower() == value.lower()
                        elif key == 'doc_type':
                            matches = matches and metadata.get('type', '').endswith(value)
                        elif key == 'category':
                            matches = matches and metadata.get('category', '') == value
                        elif key == 'source':
                            matches = matches and metadata.get('source', '') == value
                        elif key == 'sentiment':
                            matches = matches and metadata.get('sentiment', '') == value

                    if matches:
                        filtered_docs.append(doc)

                relevant_docs = filtered_docs[:limit]  # Apply limit after filtering

            # Format results with additional metadata
            results = []
            for doc in relevant_docs[:limit]:
                metadata = doc.get('metadata', {})
                result = {
                    "content": doc["content"],
                    "source": metadata.get('source', 'unknown'),
                    "type": metadata.get('type', 'unknown'),
                    "category": metadata.get('category', 'unknown'),
                    "created_at": metadata.get('created_at', ''),
                    "relevance_score": doc.get('similarity_score', 0),
                    "metadata": metadata
                }

                # Add source-specific fields
                if metadata.get('source') == 'twitter':
                    result.update({
                        "author": metadata.get('author', ''),
                        "sentiment": metadata.get('sentiment', ''),
                        "engagement": metadata.get('engagement_metrics', {})
                    })
                elif metadata.get('type', '').endswith(('_documentation', '_example')):
                    result.update({
                        "router": metadata.get('router', ''),
                        "difficulty": metadata.get('difficulty', 'intermediate')
                    })

                results.append(result)

            logger.info(f"Found {len(results)} relevant documents for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def get_router_specific_content(self, router_name: str, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get content specific to a router, optionally filtered by type"""
        try:
            # Get router documentation
            docs = await self.get_router_documentation(router_name)

            # Filter by content type if specified
            if content_type:
                docs = [doc for doc in docs if doc.get('metadata', {}).get('type', '').endswith(content_type)]

            # Get related Twitter content if available
            if not content_type or content_type == 'twitter':
                twitter_query = f"{router_name} router"
                twitter_docs = self.get_relevant_tweets(twitter_query, k=3)
                docs.extend(twitter_docs)

            logger.info(f"Retrieved {len(docs)} items for router: {router_name}")
            return docs

        except Exception as e:
            logger.error(f"Error getting router content: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []