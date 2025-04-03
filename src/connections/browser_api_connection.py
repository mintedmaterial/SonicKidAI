"""Browser API Connection for api.browser-use.com"""
import logging
import os
import json
import time
import requests
from typing import Dict, Any, Optional
import asyncio

from .base_connection import BaseConnection, Action, Parameter

logger = logging.getLogger(__name__)

class BrowserAPIConnection(BaseConnection):
    """Connection class for Browser-Use API integration"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('browser_api_key') or os.getenv('BROWSER_API_KEY')
        if not self.api_key:
            raise ValueError("Browser API key not found in config or environment variables")

        self.base_url = "https://api.browser-use.com/api/v1"
        self.current_task_id = None

        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Define available actions
        self.actions = {
            "run_task": Action(
                name="run_task",
                description="Execute a browser automation task",
                parameters=[
                    Parameter(
                        name="task",
                        required=True,
                        type=str,
                        description="Task description or instructions"
                    ),
                    Parameter(
                        name="save_browser_data",
                        required=False,
                        type=bool,
                        description="Whether to save browser cookies and data"
                    ),
                    Parameter(
                        name="override_system_message",
                        required=False,
                        type=str,
                        description="Custom system prompt for the browser agent"
                    )
                ]
            )
        }

    async def _cleanup_current_task(self) -> bool:
        """Cleanup current task if exists"""
        try:
            if self.current_task_id:
                logger.info(f"Cleaning up task: {self.current_task_id}")
                response = requests.post(
                    f"{self.base_url}/task/{self.current_task_id}/close",
                    headers=self.headers,
                    timeout=10
                )
                logger.debug(f"Task cleanup response: {response.status_code}")
                self.current_task_id = None
                return response.status_code == 200
            return True
        except Exception as e:
            logger.error(f"Error cleaning up task: {e}")
            self.current_task_id = None  # Reset anyway to avoid stuck state
            return False

    async def connect(self) -> bool:
        """Test connection to the API by attempting a simple task"""
        try:
            # Cleanup any existing task first
            await self._cleanup_current_task()

            test_task = {
                'task': 'Check browser connection',
                'save_browser_data': False
            }

            logger.debug(f"Testing connection with task: {test_task}")
            logger.debug(f"Headers: {self.headers}")

            response = requests.post(
                f"{self.base_url}/run-task",
                headers=self.headers,
                json=test_task,
                timeout=10
            )

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response body: {response.text}")

            if response.status_code == 200:
                logger.info("Successfully connected to Browser API")
                return True

            logger.error(f"Failed to connect to Browser API: Status {response.status_code} - {response.text}")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to Browser API: {str(e)}")
            return False

    async def create_task(self, task: str, save_browser_data: bool = False, override_system_message: str = None) -> Optional[str]:
        """Create a new browser automation task"""
        try:
            # Cleanup any existing task first
            await self._cleanup_current_task()

            task_data = {
                'task': task,
                'save_browser_data': save_browser_data
            }

            if override_system_message:
                task_data['override_system_message'] = override_system_message

            response = requests.post(
                f"{self.base_url}/run-task",
                headers=self.headers,
                json=task_data,
                timeout=30
            )

            logger.debug(f"Task creation response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                data = response.json()
                task_id = data.get('id')
                if task_id:
                    self.current_task_id = task_id
                    logger.info(f"Created task with ID: {task_id}")
                    return task_id

            logger.error(f"Failed to create task: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return None

    async def get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Get full task details including output"""
        try:
            response = requests.get(
                f"{self.base_url}/task/{task_id}",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                details = response.json()
                logger.debug(f"Task details: {json.dumps(details, indent=2)}")
                return details

            logger.error(f"Failed to get task details: {response.text}")
            return {'status': 'error', 'message': f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Error getting task details: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def wait_for_completion(self, task_id: str, poll_interval: float = 0.5, timeout: int = 180) -> Dict[str, Any]:
        """Poll task status until completion or timeout"""
        start_time = time.time()
        unique_steps = []

        while True:
            if time.time() - start_time > timeout:
                logger.error(f"Task timed out after {timeout} seconds")
                # Ensure cleanup even on timeout
                await self._cleanup_current_task()
                return {'status': 'timeout', 'message': f'Task timed out after {timeout} seconds'}

            try:
                details = await self.get_task_details(task_id)
                if not details:
                    logger.error("Got empty task details")
                    await self._cleanup_current_task()
                    return {'status': 'error', 'message': 'Empty task details'}

                status = details.get('status')
                new_steps = details.get('steps', [])

                # Log new steps
                if new_steps and new_steps != unique_steps:
                    for step in new_steps:
                        if step not in unique_steps:
                            logger.info(f"Task step: {json.dumps(step, indent=2)}")
                    unique_steps = new_steps.copy()

                if status in ['finished', 'failed', 'stopped', 'timeout']:
                    await self._cleanup_current_task()
                    return details

                # Reduced polling interval
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling task status: {e}")
                await self._cleanup_current_task()
                return {'status': 'error', 'message': str(e)}

    async def perform_task(self, action_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute an action with the given parameters"""
        try:
            if action_name == "run_task":
                task_instructions = params.get("task")
                if not task_instructions:
                    logger.error("Missing task instructions")
                    return None

                task_id = await self.create_task(
                    task=task_instructions,
                    save_browser_data=params.get("save_browser_data", False),
                    override_system_message=params.get("override_system_message")
                )

                if task_id:
                    logger.info(f'Task created with ID: {task_id}')
                    result = await self.wait_for_completion(
                        task_id,
                        timeout=params.get("timeout", 180)
                    )
                    if result:
                        return result
                    logger.error('Task execution failed')
                    return None
                logger.error('Task creation failed')
                return None

            else:
                logger.error(f"Unknown action: {action_name}")
                return None

        except Exception as e:
            logger.error(f"Error performing action {action_name}: {str(e)}")
            return None