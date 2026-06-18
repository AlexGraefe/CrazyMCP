from langchain.tools import tool
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

SYSTEM_PROMPT = """"You are connected to a drone swarm that you can control. For this, you have to write code in Python and give it to the swarm. Here are some examples of how to control the swarm:
land() - land the swarm
takeoff() - take off the swarm
move_forward(distance) - move the swarm forward by the given distance
move_backward(distance) - move the swarm backward by the given distance
turn_left(angle) - turn the swarm left by the given angle
turn_right(angle) - turn the swarm right by the given angle.
Try to write complete code to control the swarm, and then give it to the swarm to execute. The swarm will return the result of the code execution."""

@tool(parse_docstring=True)
def swarm_execute(code: str) -> str:
    """Give the code to the drone swarm to execute and return the result.

    Args:
        code (str): The code to execute.
    
    Returns:
        str: The result of the code execution.
    """
    print(f"Executing code: {code}")
    return f"Code executed successfully."

llm = ChatOpenAI(
    model="Qwen/Qwen3.6-27B",
    base_url="http://localhost:8000/v1",
    api_key="1"
)


agent = create_deep_agent(
    model=llm,
    tools=[swarm_execute],
    system_prompt=SYSTEM_PROMPT,
)

response = agent.invoke({"messages": [{"role": "user", "content": "Start the drones and land them."}]})
for message in response["messages"]:
    print(f"{type(message)}: {message.content}")

print("\n"*100)

respone = agent.invoke({"messages": [{"role": "user", "content": "Are the drones currently flying or on the ground?"}]})

for message in response["messages"]:
    print(f"{type(message)}: {message.content}")