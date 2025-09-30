# lang/graph/graph.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
# --- UPDATED: Import ToolNode for executing tools ---
from langgraph.prebuilt import ToolNode

from lang.state.state import AgentState
# --- UPDATED: Import the single agent node and the list of tools ---
from lang.node.node import agent_node
from lang.tools.tools import all_tools

def should_continue(state: AgentState) -> str:
    """
    Determines the next step. If the agent called a tool, we execute it.
    Otherwise, the process ends.
    """
    print("--- ROUTER: DECIDING NEXT STEP ---")
    last_message: BaseMessage = state["messages"][-1]
    
    # If the last message is an AIMessage with tool calls, we should call the tools.
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("--- Router -> Decision: Execute tools. ---")
        return "tools"
    
    # Otherwise, the agent has provided a final answer, so we end the workflow.
    print("--- Router -> Decision: End of workflow. ---")
    return END

# --- Build the New Graph ---
workflow = StateGraph(AgentState)

# Define the nodes
# The "agent" node runs our agent to decide what to do
workflow.add_node("agent", agent_node)
# The "tools" node is a special node that executes the tools our agent decides to call
workflow.add_node("tools", ToolNode(all_tools))

# Set the entry point
workflow.set_entry_point("agent")

# Add the conditional edge
# After the "agent" node runs, the "should_continue" function decides the next step
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": END,
    },
)

# Add the edge from the tools back to the agent
# After the tools are executed, the results are sent back to the agent so it can continue
workflow.add_edge("tools", "agent")

# Compile the graph
print("--- [GRAPH] Compiling the new workflow... ---")
app = workflow.compile()
print("--- [GRAPH] Workflow compiled successfully. ---")