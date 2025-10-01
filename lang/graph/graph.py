from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.prebuilt import ToolNode

from lang.state.state import AgentState
from lang.node.node import agent_node
from lang.tools.tools import all_tools

def should_continue(state: AgentState) -> str:
    """
    Determines whether the agent should continue processing or end the workflow.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        str: "tools" if the agent should execute tools, otherwise END.
    """
    print("--- ROUTER: DECIDING NEXT STEP ---")
    last_message: BaseMessage = state["messages"][-1]
    
    # If the last message is an AIMessage with tool calls, then we should call the tools.
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("--- Router -> Decision: Execute tools. ---")
        return "tools"
    
    # Otherwise, the agent has provided a final answer, so we end the workflow.
    print("--- Router -> Decision: End of workflow. ---")
    return END

# Build the graph.
workflow = StateGraph(AgentState)

# Add the agent node.
workflow.add_node("agent", agent_node)
# Add the tools node.
workflow.add_node("tools", ToolNode(all_tools))

# Set the entry point.
workflow.set_entry_point("agent")

# Add a conditional edge to determine the next step.
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": END,
    },
)

# Add an edge from the tools node back to the agent node.
workflow.add_edge("tools", "agent")

# Compile the graph.
print("--- [GRAPH] Compiling the new workflow... ---")
app = workflow.compile()
print("--- [GRAPH] Workflow compiled successfully. ---")