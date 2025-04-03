"""DeepSeek model integration for text generation"""
import logging
from typing import Dict, Any, Optional
from transformers import pipeline
from src.action_handler import register_action

logger = logging.getLogger(__name__)

# Initialize the pipeline globally for reuse
try:
    deepseek_pipeline = pipeline(
        "text-generation",
        model="deepseek-ai/DeepSeek-R1",
        trust_remote_code=True,
        device_map="auto"
    )
    logger.info("✅ Initialized DeepSeek pipeline successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize DeepSeek pipeline: {str(e)}")
    deepseek_pipeline = None

@register_action("deepseek-generate")
async def deepseek_generate(agent, **kwargs) -> Optional[Dict[str, Any]]:
    """Generate text using DeepSeek model"""
    logger.info("\n🤖 GENERATING TEXT WITH DEEPSEEK")

    try:
        # Validate required parameters
        if 'prompt' not in kwargs:
            logger.error("No prompt provided for text generation")
            return None

        if not deepseek_pipeline:
            logger.error("DeepSeek pipeline not initialized")
            return None

        # Format messages for the model
        messages = [{"role": "user", "content": kwargs['prompt']}]

        # Generate response
        result = deepseek_pipeline(messages)

        if result and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
            logger.info("✅ Text generation completed!")
            return {
                "content": generated_text,
                "model": "deepseek-ai/DeepSeek-R1"
            }
        else:
            logger.error("Text generation returned no result")
            return None

    except Exception as e:
        logger.error(f"❌ Text generation failed: {str(e)}")
        return None