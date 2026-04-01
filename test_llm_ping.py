import asyncio
from legaltech.config import get_settings

async def main():
    settings = get_settings()
    from legaltech.llm.anthropic_client import AnthropicLLM # or whatever it's called.
    print("Settings:", settings.anthropic_api_key)

if __name__ == "__main__":
    asyncio.run(main())
