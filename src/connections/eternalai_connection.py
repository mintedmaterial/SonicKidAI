"""
DEPRECATED: This file is deprecated as we're using Anthropic directly through OpenRouter.
The functionality has been moved to the Anthropic service.
Please use server/services/anthropic_service.ts instead.
"""

# This file is kept as a placeholder to prevent import errors in legacy code.
# All EternalAI functionality should use the Anthropic service instead.

class EternalAIConnection:
    """Deprecated: Use AnthropicService instead"""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "EternalAI connection is deprecated. "
            "Please use AnthropicService from server/services/anthropic_service.ts instead."
        )

    async def connect(self):
        raise NotImplementedError("Use AnthropicService instead")

    async def generate_text(self, *args, **kwargs):
        raise NotImplementedError("Use AnthropicService instead")

    async def close(self):
        raise NotImplementedError("Use AnthropicService instead")