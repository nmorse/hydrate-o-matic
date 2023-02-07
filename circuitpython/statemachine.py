import asyncio as asyncio

queue = []  
# add an element to the queue
def enqueue(item):
    global queue
    queue.append(item)

# remove an element from the queue
def dequeue():
    global queue
    if len(queue) > 0:
        return queue.pop(0)
    return None

# gets a transition for a message out of a state 
def getTransition(state, message):
    if "on" in state and message in state["on"]:
        return state["on"][message]
    return None

# gets a state given a state_name 
def getState(states, state_name):
    if state_name in states:
        return states[state_name]
    return None

# an interpreter for xstate/statley.ai statemachines (note: only basic features are handled)
async def xstate_interpreter(state_machine):
    state_name = state_machine["initial"]
    state = getState(state_machine["states"], state_name)
    if state != None and "entry" in state:
        state["entry"](state)
    while state != None:
        msg = dequeue()
        if msg != None:
            t = getTransition(state, msg)
            if t != None:
                if (t["target"] != state_name) and "exit" in state:
                    state["exit"](state)
                last_state_name = state_name
                # now make the jump to the next state
                state_name = t["target"]
                state = getState(state_machine["states"], state_name)
                if state != None and (state_name != last_state_name) and "entry" in state:
                    state["entry"](state)
        await asyncio.sleep(0)
    print("Error: No state ", state_name, " found")