import asyncio

from weschatbot.utils.limiter import limiter


@limiter(user_id=1, interval=10, limit=2)
async def hello():
    print("hello")


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(hello())
    loop.run_until_complete(hello())
    loop.run_until_complete(hello())
