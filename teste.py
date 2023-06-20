import asyncio
from src.modules.utils.aichat import AIChat


async def main():
    aichat = AIChat()
    print(await aichat.chat(None, 'Toca qualquer música ai doido'))


if __name__ == '__main__':
    asyncio.run(main())
