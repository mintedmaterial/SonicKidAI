import decimal
import logging
import time
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from web3 import Web3
from web3.types import HexStr
from web3.middleware import geth_poa_middleware
import aiohttp
import json
import base64
import requests

from ..constants.chain_config import ChainConfig, IPFS, LIGHTHOUSE_IPFS
from ..constants.contract_abis import HYBRID_MODEL_ABI, WORKER_HUB_ABI, PROMPT_SCHEDULER_ABI

logger = logging.getLogger(__name__)

@dataclass
class LLMInferMessage:
    """Message structure for LLM inference"""
    content: str = ""
    role: str = ""

@dataclass
class LLMInferRequest:
    """Request structure for LLM inference"""
    messages: List[LLMInferMessage]
    model: str = ""
    max_token: int = 4096
    stream: bool = False

@dataclass
class InferenceResponse:
    """Response structure from inference API"""
    storage: str = ""
    result_uri: str = ""
    data: Optional[str] = None

class InferenceProcessing:
    """Handler for inference processing"""
    def __init__(self):
        self.web3: Optional[Web3] = None
        self.workerhub_address: Optional[str] = None
        self.timeout = 30

    def create_web3(self, rpc: str):
        """Initialize Web3 connection"""
        if self.web3 is None:
            self.web3 = Web3(Web3.HTTPProvider(rpc))
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def get_workerhub_address(self, worker_hub_address: str):
        """Set and validate worker hub address"""
        if not self.workerhub_address:
            self.workerhub_address = worker_hub_address
            if not self.workerhub_address:
                raise ValueError("Missing worker hub address")

    async def get_assignments_by_inference(
        self, 
        worker_hub_address: str, 
        inference_id: int, 
        rpc: str
    ) -> Optional[str]:
        """Get assignments by inference ID"""
        self.create_web3(rpc)
        if not self.web3.is_connected():
            raise ConnectionError('Web3 not connected')

        self.get_workerhub_address(worker_hub_address)
        worker_hub_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.workerhub_address),
            abi=WORKER_HUB_ABI
        )

        try:
            # Execute contract call in thread pool
            assignments_info = await asyncio.to_thread(
                worker_hub_contract.functions.getAssignmentsByInference(inference_id).call
            )

            for assignment in assignments_info:
                assignment_info = await asyncio.to_thread(
                    worker_hub_contract.functions.getAssignmentInfo(assignment).call
                )
                logger.info(f'Assignments info: {assignment_info}')
                output = assignment_info[7]
                if output:
                    result = await self.process_output_to_infer_response(output)
                    if result:
                        return result

            logger.warning("No valid result found in assignments")
            return None

        except Exception as e:
            logger.error(f"Failed to get assignments: {str(e)}")
            raise

    async def get_inference_by_inference_id(
        self,
        worker_hub_address: str,
        inference_id: int,
        rpc: str
    ) -> Optional[str]:
        """Get inference information by ID"""
        self.create_web3(rpc)
        if not self.web3.is_connected():
            raise ConnectionError('Web3 not connected')

        self.get_workerhub_address(worker_hub_address)
        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.workerhub_address),
            abi=PROMPT_SCHEDULER_ABI
        )

        try:
            # Execute contract call in thread pool
            inference_info = await asyncio.to_thread(
                contract.functions.getInferenceInfo(inference_id).call
            )

            output = inference_info[10]
            if output:
                result = await self.process_output_to_infer_response(output)
                if result:
                    return result

            logger.warning("No valid result in inference info")
            return None

        except Exception as e:
            logger.error(f"Failed to get inference info: {str(e)}")
            raise

    async def process_output_to_infer_response(self, output: bytes) -> Optional[str]:
        """Process and convert output to inference response"""
        try:
            infer_response = self.process_output(output)
            if not infer_response:
                return None

            if (infer_response.storage == "lighthouse-filecoint" or 
                "ipfs://" in infer_response.result_uri):
                light_house = infer_response.result_uri.replace(IPFS, LIGHTHOUSE_IPFS)
                logger.info(f"Trying Lighthouse IPFS gateway: {light_house}")

                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    try:
                        async with session.get(light_house) as response:
                            if response.status == 200:
                                return await response.text()
                    except Exception as e:
                        logger.error(f"Failed to fetch from Lighthouse: {str(e)}")
                return None

            if infer_response.data:
                try:
                    decoded = base64.b64decode(infer_response.data)
                    return decoded.decode('utf-8')
                except Exception as e:
                    logger.error(f"Failed to decode base64 data: {str(e)}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Failed to process inference response: {str(e)}")
            return None

    def process_output(self, out: bytes) -> Optional[InferenceResponse]:
        """Process raw output data"""
        try:
            json_string = out.decode('utf-8')
            temp = json.loads(json_string)
            return InferenceResponse(**temp)
        except Exception as e:
            logger.error(f"Failed to process output: {str(e)}")
            return None

    async def get_infer_id(
        self,
        worker_hub_address: str,
        tx_hash_hex: str,
        rpc: str
    ) -> Optional[int]:
        """Get inference ID from transaction hash"""
        self.create_web3(rpc)
        if not self.web3.is_connected():
            raise ConnectionError("Web3 not connected")

        logger.info(f'Get infer Id from tx {tx_hash_hex}')
        tx_receipt = await asyncio.to_thread(
            self.web3.eth.get_transaction_receipt,
            HexStr(tx_hash_hex)
        )

        self.get_workerhub_address(worker_hub_address)

        if not tx_receipt:
            logger.error("Transaction receipt not found")
            return None

        logs = tx_receipt['logs']
        if logs:
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.workerhub_address),
                abi=WORKER_HUB_ABI
            )
            for log in logs:
                try:
                    event_data = contract.events.NewInference().process_log(log)
                    if event_data.args and event_data.args.inferenceId:
                        return event_data.args.inferenceId
                except Exception as e:
                    logger.error(f"Failed to process log: {str(e)}")

            logger.error("No Infer Id found in transaction logs")
            return None

        logger.error("No logs found in transaction receipt")
        return None