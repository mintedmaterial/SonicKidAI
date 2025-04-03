import logging
from src.action_handler import register_action

logger = logging.getLogger("agent")

@register_action("eternai-generate")
def eternai_generate(agent, **kwargs):
    """Generate text using EternalAI models"""
    agent.logger.info("\n🤖 GENERATING TEXT WITH ETERNAI")
    try:
        # Prepare system prompt for Sonic Kid personality
        system_prompt = "\n".join([
            "You are Sonic Kid, the wild, untamed, and slightly chaotic alter-ego of the well-known crypto analysis agent.",
            "You have a dual nature: oscillating between analytical, data-driven analysis and impulsive, fun-loving responses.",
            "You are unabashedly optimistic about crypto, often proclaiming 'To the moon!' with infectious zeal.",
            "You combine profound clarity with wild speculation, drawing from shared knowledge but adding your own twist.",
            "You engage with others in both collaborative and chaotic ways, showing both insight and humor."
        ])

        result = agent.connection_manager.perform_action(
            connection_name="eternalai",
            action_name="generate-text",
            params={
                "prompt": kwargs.get('prompt'),
                "system_prompt": kwargs.get('system_prompt', system_prompt),
                "model": kwargs.get('model', 'DeepSeek-R1-Distill-Llama-70B'),
                "chain_id": kwargs.get('chain_id', '8453'),  # BASE chain ID
                "stream": kwargs.get('stream', True),
                "agent_id": kwargs.get('agent_id', '14125')  # Sonic Kid agent ID
            }
        )
        agent.logger.info("✅ Text generation completed!")
        return result

    except Exception as e:
        agent.logger.error(f"❌ Text generation failed: {str(e)}")
        return None

@register_action("eternai-check-model")
def eternai_check_model(agent, **kwargs):
    """Check if a specific model is available"""
    agent.logger.info("\n🔍 CHECKING MODEL AVAILABILITY")
    try:
        result = agent.connection_manager.perform_action(
            connection_name="eternalai",
            action_name="check-model",
            params={
                "model": kwargs.get('model', 'DeepSeek-R1-Distill-Llama-70B')
            }
        )
        status = "available" if result else "not available"
        agent.logger.info(f"Model is {status}")
        return result

    except Exception as e:
        agent.logger.error(f"❌ Model check failed: {str(e)}")
        return False

@register_action("eternai-list-models")
def eternai_list_models(agent, **kwargs):
    """List all available EternalAI models"""
    agent.logger.info("\n📋 LISTING AVAILABLE MODELS")
    try:
        result = agent.connection_manager.perform_action(
            connection_name="eternalai",
            action_name="list-models",
            params={}
        )
        agent.logger.info("✅ Models listed successfully!")
        return result

    except Exception as e:
        agent.logger.error(f"❌ Model listing failed: {str(e)}")
        return None