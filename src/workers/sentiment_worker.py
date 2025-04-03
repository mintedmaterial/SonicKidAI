"""Background worker for handling sentiment analysis tasks"""
import asyncio
import logging
import json
from typing import Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

class SentimentWorker:
    """Worker for handling sentiment analysis tasks"""
    _instance = None
    _model = None
    _tokenizer = None
    _queue = asyncio.Queue()
    _processing = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SentimentWorker, cls).__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize the worker and model"""
        if self._model is None:
            try:
                logger.info("Initializing sentiment analysis worker...")
                model_name = "ElKulako/cryptobert"
                
                # Load tokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    use_fast=True,
                    local_files_only=False
                )

                # Load model
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    local_files_only=False
                )
                self._model.eval()
                
                logger.info("✅ Worker initialized successfully")
                
                # Start processing loop
                asyncio.create_task(self._process_queue())
            except Exception as e:
                logger.error(f"Failed to initialize worker: {str(e)}")
                raise

    async def _process_queue(self):
        """Process tasks from the queue"""
        self._processing = True
        while self._processing:
            try:
                task = await self._queue.get()
                if task is None:  # Shutdown signal
                    break
                    
                text, callback = task
                try:
                    result = await self._analyze_text(text)
                    if callback:
                        await callback(result)
                except Exception as e:
                    logger.error(f"Error processing task: {str(e)}")
                finally:
                    self._queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on errors
                
        self._processing = False

    async def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text sentiment"""
        try:
            # Tokenize
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            # Get prediction
            with torch.no_grad():
                outputs = self._model(**inputs)
                scores = torch.nn.functional.softmax(outputs.logits, dim=1)
                sentiment_score = float(scores[0][1])

            # Format response
            label = "bullish" if sentiment_score > 0.5 else "bearish"
            confidence = sentiment_score if sentiment_score > 0.5 else (1 - sentiment_score)

            return {
                "label": label,
                "score": round(confidence, 4),
                "source": "cryptobert_worker"
            }

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {"error": str(e)}

    async def submit_task(self, text: str, callback=None) -> None:
        """Submit a text for analysis"""
        await self._queue.put((text, callback))

    async def shutdown(self):
        """Shutdown the worker"""
        self._processing = False
        await self._queue.put(None)  # Signal to stop
        self._model = None
        self._tokenizer = None
        torch.cuda.empty_cache()
