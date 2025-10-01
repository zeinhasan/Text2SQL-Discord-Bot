from typing import List, TypedDict, Annotated, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Defines the state structure for the agent graph.

    This TypedDict is used to pass data between the nodes of the LangGraph workflow.

    Attributes:
        messages: A list of messages in the conversation history. The `add_messages`
                  annotator ensures that new messages are always appended.
    """
    messages: Annotated[List[BaseMessage], add_messages]