import asyncio
from statemachine import xstate_interpreter
from states import hydrominder_states, time_out_click


async def main():
    async_statemachine = asyncio.create_task(xstate_interpreter(hydrominder_states))
    async_timer_message = asyncio.create_task(time_out_click())
    await asyncio.gather(async_statemachine, async_timer_message)

asyncio.run(main())
