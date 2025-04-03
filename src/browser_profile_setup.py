"""Browser automation using Browser Use Cloud API"""
import os
import sys
from pathlib import Path
from typing import Dict, Any
import logging
import aiohttp
import json
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BrowserManager:
    """Manage browser automation with Browser Use Cloud API"""
    def __init__(self):
        self.task_id = None
        self.browser_api_key = os.getenv('BROWSER_API_KEY')
        if not self.browser_api_key:
            raise ValueError("BROWSER_API_KEY environment variable not found")
        self.base_url = "https://api.browser-use.com/api/v1"
        self.last_seen_step = None

    async def _create_task(self, task_description: str, save_browser_data: bool = False, 
                          wait_for_network_idle: bool = False, override_system_message: str = None) -> Dict[str, Any]:
        """Create a new browser automation task"""
        url = f"{self.base_url}/run-task"
        headers = {
            "Authorization": f"Bearer {self.browser_api_key}",
            "Content-Type": "application/json"
        }

        # Build task payload according to API documentation
        payload = {
            "task": task_description,
            "browser_config": {
                "headless": True,
                "save_browser_data": save_browser_data,
                "wait_for_network_idle": wait_for_network_idle
            }
        }

        # Add optional system message if provided
        if override_system_message:
            payload["system_message"] = override_system_message

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Creating task with payload: {json.dumps(payload, indent=2)}")
                logger.debug(f"Using headers: {headers}")

                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"API Response Status: {response.status}")
                    logger.debug(f"API Response: {response_text}")

                    if response.status != 200:
                        logger.error(f"Failed to create task. Status: {response.status}, Response: {response_text}")
                        return {
                            "success": False,
                            "error": f"Failed to create browser task: {response_text}"
                        }

                    data = await response.json()
                    self.task_id = data.get('id')
                    logger.info(f"✅ Browser task created with ID: {self.task_id}")
                    return {
                        "success": True,
                        "task_id": self.task_id,
                        **data
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Network error creating task: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to connect to Browser Use API: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _stop_task(self, task_id: str) -> bool:
        """Stop a running browser automation task"""
        url = f"{self.base_url}/stop-task"
        headers = {
            "Authorization": f"Bearer {self.browser_api_key}"
        }
        params = {"task_id": task_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Failed to stop task {task_id}: {response_text}")
                        return False
                    logger.info(f"✅ Task {task_id} stopped successfully")
                    return True
        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {str(e)}")
            return False

    async def _get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current task status"""
        url = f"{self.base_url}/task/{task_id}/status"
        headers = {"Authorization": f"Bearer {self.browser_api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Failed to get task status: {response_text}")
                        return {
                            "success": False,
                            "error": f"Failed to get task status: {response_text}"
                        }

                    response_data = await response.json()
                    if isinstance(response_data, str):
                        return {"status": response_data}
                    return response_data

        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Get full task details including output"""
        url = f"{self.base_url}/task/{task_id}"
        headers = {"Authorization": f"Bearer {self.browser_api_key}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Failed to get task details: {response_text}")
                        return {
                            "success": False,
                            "error": f"Failed to get task details: {response_text}"
                        }

                    response_data = await response.json()
                    if isinstance(response_data, str):
                        return {"status": "error", "error": response_data}
                    return response_data

        except Exception as e:
            logger.error(f"Error getting task details: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _wait_for_completion(self, task_id: str, timeout: int = 120, poll_interval: int = 2) -> Dict[str, Any]:
        """Poll task status until completion or timeout"""
        start_time = time.time()
        seen_steps = set()
        error_count = 0
        max_errors = 3

        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                logger.error(f"Task {task_id} timed out after {timeout} seconds")
                await self._stop_task(task_id)
                return {
                    "success": False,
                    "error": f"Task timed out after {timeout} seconds"
                }

            try:
                # Get task details and status
                details = await self._get_task_details(task_id)
                if details.get("success") is False:
                    error_count += 1
                    if error_count >= max_errors:
                        await self._stop_task(task_id)
                        return details
                    await asyncio.sleep(poll_interval)
                    continue

                # Log new steps only
                steps = details.get('steps', [])
                for step in steps:
                    step_id = step.get('id')
                    if step_id and step_id not in seen_steps:
                        seen_steps.add(step_id)
                        logger.info(f"Task step: {json.dumps(step, indent=2)}")

                # Check completion status
                status = details.get('status')
                if status == 'finished':
                    logger.info("✅ Task completed successfully")
                    await self._stop_task(task_id)
                    return {
                        "success": True,
                        "task_id": task_id,
                        "output": details.get('output'),
                        "steps": details.get('steps', []),
                        "status": status
                    }
                elif status in ['failed', 'stopped', 'error']:
                    error_msg = details.get('error', 'Unknown error')
                    logger.error(f"Task failed with status {status}: {error_msg}")
                    await self._stop_task(task_id)
                    return {
                        "success": False,
                        "error": error_msg
                    }

            except Exception as e:
                error_count += 1
                logger.error(f"Error while polling task: {str(e)}")
                if error_count >= max_errors:
                    await self._stop_task(task_id)
                    return {
                        "success": False,
                        "error": f"Too many errors while polling task: {str(e)}"
                    }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def execute_task(self, task_description: str, timeout: int = 120, 
                         save_browser_data: bool = False, wait_for_network_idle: bool = False, 
                         override_system_message: str = None) -> Dict[str, Any]:
        """Execute a browser automation task and wait for results"""
        try:
            # Create and run task
            task_data = await self._create_task(
                task_description,
                save_browser_data=save_browser_data,
                wait_for_network_idle=wait_for_network_idle,
                override_system_message=override_system_message
            )

            if not task_data.get("success"):
                return task_data

            task_id = task_data["task_id"]

            # Wait for task completion
            logger.info(f"Waiting for task {task_id} to complete...")
            result = await self._wait_for_completion(task_id, timeout=timeout)

            return result

        except Exception as e:
            logger.error(f"Error executing browser task: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

async def test_browser():
    """Test the browser automation functionality"""
    try:
        # Initialize browser manager
        manager = BrowserManager()
        logger.info("Testing browser automation...")

        # Test simple navigation with extended timeout
        result = await manager.execute_task(
            "Go to google.com and search for Browser Use",
            timeout=120,
            wait_for_network_idle=True
        )
        logger.info(f"Task result: {json.dumps(result, indent=2)}")

        return True

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(test_browser())
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    except Exception as e:
        logger.error(f"Test runner error: {str(e)}")