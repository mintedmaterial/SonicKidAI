import logging
from src.action_handler import register_action

logger = logging.getLogger("agent")

@register_action("openrouter-generate")
def openrouter_generate(agent, **kwargs):
    """Generate text using OpenRouter models"""
    agent.logger.info("\n🤖 GENERATING TEXT WITH OPENROUTER")
    try:
        result = agent.connection_manager.perform_action(
            connection_name="anthropic",  # Using openrouter connection for Anthropic
            action_name="generate-text",
            params=[
                kwargs.get('prompt'),
                kwargs.get('system_prompt', agent._construct_system_prompt()),
                kwargs.get('model', None)
            ]
        )
        agent.logger.info("✅ Text generation completed!")
        return result
    except Exception as e:
        agent.logger.error(f"❌ Text generation failed: {str(e)}")
        return None

@register_action("openrouter-check-model")
def openrouter_check_model(agent, **kwargs):
    """Check if a specific model is available on OpenRouter"""
    agent.logger.info("\n🔍 CHECKING MODEL AVAILABILITY")
    try:
        result = agent.connection_manager.perform_action(
            connection_name="anthropic",
            action_name="verify_model",
            params=[kwargs.get('model')]
        )
        status = "available" if result else "not available"
        agent.logger.info(f"Model is {status}")
        return result
    except Exception as e:
        agent.logger.error(f"❌ Model check failed: {str(e)}")
        return False

@register_action("openrouter-list-models")
def openrouter_list_models(agent, **kwargs):
    """List all available OpenRouter models"""
    agent.logger.info("\n📋 LISTING AVAILABLE MODELS")
    try:
        result = agent.connection_manager.perform_action(
            connection_name="eternalai",
            action_name="list-models",
            params=[]
        )
        agent.logger.info("✅ Models listed successfully!")
        return result
    except Exception as e:
        agent.logger.error(f"❌ Model listing failed: {str(e)}")
        return None
