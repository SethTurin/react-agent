"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

# from datetime import datetime, timezone
# from typing import Dict, List, Literal, cast

# from langchain_core.messages import AIMessage
# from langchain_core.runnables import RunnableConfig
# from langgraph.graph import StateGraph
# from langgraph.prebuilt import ToolNode

# from react_agent.configuration import Configuration
# from react_agent.state import InputState, State
# from react_agent.tools import TOOLS
# from react_agent.utils import load_chat_model

# # Define the function that calls the model


# async def call_model(
#     state: State, config: RunnableConfig
# ) -> Dict[str, List[AIMessage]]:
#     """Call the LLM powering our "agent".

#     This function prepares the prompt, initializes the model, and processes the response.

#     Args:
#         state (State): The current state of the conversation.
#         config (RunnableConfig): Configuration for the model run.

#     Returns:
#         dict: A dictionary containing the model's response message.
#     """
#     configuration = Configuration.from_runnable_config(config)

#     # Initialize the model with tool binding. Change the model or add more tools here.
#     model = load_chat_model(configuration.model).bind_tools(TOOLS)

#     # Format the system prompt. Customize this to change the agent's behavior.
#     system_message = configuration.system_prompt.format(
#         system_time=datetime.now(tz=timezone.utc).isoformat()
#     )

#     # Get the model's response
#     response = cast(
#         AIMessage,
#         await model.ainvoke(
#             [{"role": "system", "content": system_message}, *state.messages], config
#         ),
#     )

#     # Handle the case when it's the last step and the model still wants to use a tool
#     if state.is_last_step and response.tool_calls:
#         return {
#             "messages": [
#                 AIMessage(
#                     id=response.id,
#                     content="Sorry, I could not find an answer to your question in the specified number of steps.",
#                 )
#             ]
#         }

#     # Return the model's response as a list to be added to existing messages
#     return {"messages": [response]}


# # Define a new graph

# builder = StateGraph(State, input=InputState, config_schema=Configuration)

# # Define the two nodes we will cycle between
# builder.add_node(call_model)
# builder.add_node("tools", ToolNode(TOOLS))

# # Set the entrypoint as `call_model`
# # This means that this node is the first one called
# builder.add_edge("__start__", "call_model")


# def route_model_output(state: State) -> Literal["__end__", "tools"]:
#     """Determine the next node based on the model's output.

#     This function checks if the model's last message contains tool calls.

#     Args:
#         state (State): The current state of the conversation.

#     Returns:
#         str: The name of the next node to call ("__end__" or "tools").
#     """
#     last_message = state.messages[-1]
#     if not isinstance(last_message, AIMessage):
#         raise ValueError(
#             f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
#         )
#     # If there is no tool call, then we finish
#     if not last_message.tool_calls:
#         return "__end__"
#     # Otherwise we execute the requested actions
#     return "tools"


# # Add a conditional edge to determine the next step after `call_model`
# builder.add_conditional_edges(
#     "call_model",
#     # After call_model finishes running, the next node(s) are scheduled
#     # based on the output from route_model_output
#     route_model_output,
# )

# # Add a normal edge from `tools` to `call_model`
# # This creates a cycle: after using tools, we always return to the model
# builder.add_edge("tools", "call_model")

# # Compile the builder into an executable graph
# # You can customize this by adding interrupt points for state updates
# graph = builder.compile(
#     interrupt_before=[],  # Add node names here to update state before they're called
#     interrupt_after=[],  # Add node names here to update state after they're called
# )
# graph.name = "ReAct Agent"  # This customizes the name in LangSmith



"""Simple script that performs human interaction and returns the result."""

from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.types import interrupt
from langchain_core.messages import ToolMessage
from typing_extensions import Literal

# Define the state schema
class State(TypedDict):
    messages: list

# Define the human interaction node
def human_interaction_node(state: State):
    # Prepare the interrupt request
    human_interrupt = {
        "action_request": {
            "action": "human_assistance",
            "args": {
                "query": "Please provide the necessary information."
            }
        },
        "config": {
            "allow_accept": True,
            "allow_edit": True,
            "allow_respond": True,
            "allow_ignore": True
        },
        "description": "The assistant is requesting human assistance."
    }
    # Call interrupt and wait for human response
    human_response = interrupt([human_interrupt])[0]
    # Return the human response as a ToolMessage
    return {
        "messages": [
            ToolMessage(
                content=human_response["args"]["response"],
                tool_call_id=human_response.get("tool_call_id", "human_interaction")
            )
        ]
    }

# Define the graph
graph_builder = StateGraph(State)

# Add the human interaction node
graph_builder.add_node("human_interaction_node", human_interaction_node)

# Set the entry point
graph_builder.set_entry_point("human_interaction_node")

# Compile the graph
graph = graph_builder.compile()
