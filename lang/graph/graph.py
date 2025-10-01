from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from lang.state.state import AgentState
from lang.node.node import agent_node
from lang.tools.tools import all_tools

def should_continue(state: AgentState) -> str:
    """
    Determines the next step in the workflow.
    """
    print("--- [ROUTER] Deciding next step ---")
    if hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls:
        print("--- [ROUTER] -> Decision: Execute tools. ---")
        return "tools"
    
    print("--- [ROUTER] -> Decision: End of workflow. ---")
    return END

# --- Build the Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(all_tools))

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
workflow.add_edge("tools", "agent")

# Compile the graph into a runnable application.
app = workflow.compile()