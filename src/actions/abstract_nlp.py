import os
import logging
from typing import Dict, Any, Optional
import requests
from ..connections.base_connection import BaseConnection

logger = logging.getLogger("actions.abstract_nlp")

async def transfer(agent: Any, to_address: str, amount: float, token_address: Optional[str] = None) -> Dict[str, Any]:
    """Execute a token transfer on Abstract protocol"""
    try:
        if not hasattr(agent, 'connection_manager'):
            raise AttributeError("Agent must have a connection_manager")

        abstract_connection = agent.connection_manager.connections.get("abstract")
        if not abstract_connection:
            raise ValueError("No Abstract connection found")

        result = await abstract_connection.transfer(
            to_address=to_address,
            amount=amount,
            token_address=token_address
        )
        return result

    except Exception as e:
        logger.error(f"Failed to send tokens: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def parse_transaction_command(text: str) -> Dict[str, Any]:
    """
    Parse natural language transaction commands using EternalAI API.

    Examples:
    - "Send 100 USDC to 0xCCa8009f5e09F8C5dB63cb0031052F9CB635Af62"
    - "Transfer 0.1 ETH to 0xbD8679cf79137042214fA4239b02F4022208EE82"
    - "Pay 50 USDC on Abstract to [address]"
    """
    try:
        api_key = "5a693905b3aa8160ff2941f0a42058c100ea2af2ba54e53864ee1166fa6810b7"
        if not api_key:
            raise ValueError("No EternalAI API key provided")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = """
        You are a transaction command parser. Extract transaction details from natural language commands.
        Return a JSON object with these fields:
        - action: "transfer" or "send" or "pay"
        - amount: numeric value
        - token: token symbol (e.g., "ETH", "USDC")
        - to_address: Ethereum address
        - network: "abstract" if specified, otherwise null
        """

        response = requests.post(
            "https://api.eternalai.org/v1/chat/completions",
            headers=headers,
            json={
                "chain_id": "8453",  # Base network
                "model": "DeepSeek-R1-Distill-Llama-70B",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "response_format": {"type": "json_object"}
            }
        )

        if response.status_code != 200:
            raise Exception(f"Error code: {response.status_code} - {response.text}")

        data = response.json()
        parsed = data['choices'][0]['message']['content']
        return parsed

    except Exception as e:
        logger.error(f"Failed to parse transaction command: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to parse command: {str(e)}"
        }

async def execute_nlp_command(agent, command: str) -> Dict[str, Any]:
    """Execute a natural language transaction command"""
    try:
        # Parse the command
        parsed = parse_transaction_command(command)
        if not parsed.get("success", True):
            return parsed

        # Validate parsed data
        if not all(k in parsed for k in ["action", "amount", "token", "to_address"]):
            return {
                "success": False,
                "error": "Invalid command format. Please specify amount, token, and recipient address."
            }

        # Execute the transfer
        result = await transfer(
            agent,
            to_address=parsed["to_address"],
            amount=parsed["amount"],
            token_address=None if parsed["token"] == "ETH" else f"TOKEN_{parsed['token']}"
        )

        if result["success"]:
            return {
                "success": True,
                "message": f"Successfully executed: {command}",
                "transaction_hash": result["transaction_hash"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    except Exception as e:
        logger.error(f"Failed to execute NLP command: {str(e)}")
        return {
            "success": False,
            "error": f"Command execution failed: {str(e)}"
        }