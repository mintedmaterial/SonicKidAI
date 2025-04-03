import logging
from typing import Any, List, Optional, Type, Dict
from src.connections.base_connection import BaseConnection
from src.connections.discord_connection import DiscordConnection
from src.connections.openocean_base_connection import OpenOceanBaseConnection

logger = logging.getLogger("connection_manager")

class ConnectionManager:
    def __init__(self, agent_config):
        """Initialize connection manager with configuration"""
        self.connections: Dict[str, BaseConnection] = {}
        self.primary_llm = None
        for config in agent_config:
            self._register_connection(config)

    @staticmethod
    def _class_name_to_type(class_name: str) -> Optional[Type[BaseConnection]]:
        """Map connection names to their corresponding classes"""
        connection_map = {
            "discord": DiscordConnection,  # Discord connection mapping
            "openocean": OpenOceanBaseConnection,  # OpenOcean DEX connection
        }
        return connection_map.get(class_name)

    def _register_connection(self, config_dic: Dict[str, Any]) -> None:
        """Register a new connection with configuration"""
        try:
            name = config_dic["name"]
            connection_class = self._class_name_to_type(name)
            if connection_class is None:
                logger.error(f"Unknown connection type: {name}")
                return

            # Initialize connection with config
            connection = connection_class(config_dic)
            self.connections[name] = connection
            logger.info(f"Registered c: {name}")

        except KeyError as ke:
            logger.error(f"Missing required configuration key: {ke}")
        except Exception as e:
            logger.error(f"Failed to initialize connection {config_dic.get('name', 'unknown')}: {e}")

    async def configure_connection(self, connection_name: str) -> bool:
        """Configure a specific connection with validation"""
        try:
            connection = self.connections[connection_name]
            success = await connection.configure()

            if success:
                logger.info(f"\n✅ SUCCESSFULLY CONFIGURED CONNECTION: {connection_name}")
            else:
                logger.error(f"\n❌ ERROR CONFIGURING CONNECTION: {connection_name}")
            return success

        except KeyError:
            logger.error("\nUnknown connection. Try 'list-connections' to see all supported connections.")
            return False
        except Exception as e:
            logger.error(f"\nAn error occurred during configuration: {e}")
            return False

    async def list_connections(self) -> None:
        """List all available connections and their status"""
        try:
            logger.info("\nAVAILABLE CONNECTIONS:")
            for name, connection in self.connections.items():
                status = "✅ Configured" if await connection.is_configured() else "❌ Not Configured"
                logger.info(f"- {name}: {status}")
        except Exception as e:
            logger.error(f"Error listing connections: {e}")

    def list_actions(self, connection_name: str) -> None:
        """List all available actions for a specific connection"""
        try:
            connection = self.connections[connection_name]

            if connection.is_configured():
                logger.info(
                    f"\n✅ {connection_name} is configured. You can use any of its actions."
                )
            else:
                logger.info(
                    f"\n❌ {connection_name} is not configured. You must configure a connection to use its actions."
                )

            logger.info("\nAVAILABLE ACTIONS:")
            for action_name, action in connection.actions.items():
                logger.info(f"- {action_name}: {action.description}")
                logger.info("  Parameters:")
                for param in action.parameters:
                    req = "required" if param.required else "optional"
                    logger.info(f"    - {param.name} ({req}): {param.description}")

        except KeyError:
            logger.error(
                "\nUnknown connection. Try 'list-connections' to see all supported connections."
            )
        except Exception as e:
            logger.error(f"\nAn error occurred: {e}")

    async def perform_action(
        self, connection_name: str, action_name: str, params: Dict[str, Any]
    ) -> Optional[Any]:
        """Perform an action on a specific connection"""
        try:
            connection = self.connections[connection_name]

            if not await connection.is_configured():
                logger.error(f"\nError: Connection '{connection_name}' is not configured")
                return None

            if action_name not in connection.actions:
                logger.error(
                    f"\nError: Unknown action '{action_name}' for connection '{connection_name}'"
                )
                return None

            return await connection.perform_action(action_name, params)

        except Exception as e:
            logger.error(
                f"\nAn error occurred while trying action {action_name} for {connection_name} connection: {e}"
            )
            return None

    def get_model_providers(self) -> List[str]:
        """Get a list of all LLM provider connections"""
        return [
            name
            for name, conn in self.connections.items()
            if conn.is_configured() and getattr(conn, "is_llm_provider", False)
        ]

    @property
    def primary_provider(self) -> Optional[BaseConnection]:
        """Get the primary LLM provider"""
        return self.primary_llm