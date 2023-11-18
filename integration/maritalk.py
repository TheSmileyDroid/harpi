import asyncio
from src.res.utils.aichat import AIChat


async def main():
    chat = AIChat()

    while True:
        ask = input("SmileyDroid: ")
        if ask == "reset":
            chat.reset()
            continue
        elif ask == "mem":
            print(chat.chat_mem)
            continue
        elif ask == "exit":
            break
        response = await chat.get_response(ask)

        print(response)


if __name__ == "__main__":
    print("Initializing...")
    asyncio.run(main())
