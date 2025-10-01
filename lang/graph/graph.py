from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from lang.state.state import AgentState
from lang.node.node import agent_node, generate_image_node
from lang.tools.tools import all_tools
import re

def route_to_image_or_agent(state: AgentState) -> str:
    """
    Routes the workflow to either the image generation node or the general agent
    based on the content of the user's last message.
    """
    print("--- [ROUTER] Deciding workflow path... ---")
    last_message = state["messages"][-1]
    
    prompt_text = ""
    image_data_exists = False

    # Handle cases where the message contains both text and images.
    if isinstance(last_message.content, list):
        for part in last_message.content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    prompt_text = part.get("text", "").lower()
                if part.get("type") == "image_url":
                    # We only need to know if an image exists, not its content
                    image_data_exists = True
    else:
        # Fallback for text-only messages
        prompt_text = str(last_message.content).lower()

    # Keywords to trigger the image generation path
    image_keywords = ["generate", "create", "draw", "modify", "edit", "style", "design", "image", "photo"]

    # The user's prompt MUST contain an image keyword OR they must have uploaded an image.
    if any(keyword in prompt_text for keyword in image_keywords) or image_data_exists:
        print("--- [ROUTER] -> Decision: Route to dedicated image generation node. ---")
        return "generate_image_node"
    
    print("--- [ROUTER] -> Decision: Route to general agent. ---")
    return "agent"

def should_continue(state: AgentState) -> str:
    """
    Determines whether the general agent should continue using tools or end the workflow.
    """
    print("--- [AGENT_ROUTER] Deciding next step for agent... ---")
    if hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls:
        print("--- [AGENT_ROUTER] -> Decision: Execute tools. ---")
        return "tools"
    
    print("--- [AGENT_ROUTER] -> Decision: End of workflow. ---")
    return END

# --- Build the Graph ---
workflow = StateGraph(AgentState)

# Define the nodes for the graph.
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(all_tools))
workflow.add_node("generate_image_node", generate_image_node)

# --- Wire the Graph ---
# Set the conditional entry point to route to the correct node.
workflow.set_conditional_entry_point(
    route_to_image_or_agent,
    {
        "generate_image_node": "generate_image_node",
        "agent": "agent"
    }
)

# Define the edges for the general agent workflow.
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
workflow.add_edge("tools", "agent")

# Define the edge for the image generation workflow.
workflow.add_edge("generate_image_node", END)

# Compile the graph into a runnable application
app = workflow.compile()