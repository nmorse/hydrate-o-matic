import asyncio
import statemachine
from states import hydrominder_states

async def toggle_timer(rate):
    while True:
        await asyncio.sleep(rate)
        statemachine.enqueue("toggle")

async def main():
    async_statemachine = asyncio.create_task(statemachine.xstate_interpreter(hydrominder_states))
    async_timer_message = asyncio.create_task(toggle_timer(0.5))
    await asyncio.gather(async_statemachine, async_timer_message)

asyncio.run(main())
