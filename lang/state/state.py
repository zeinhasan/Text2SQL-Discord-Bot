from typing import List, TypedDict, Annotated, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Represents the state of our agent graph.

    This TypedDict defines the structure of the data that is passed between
    the nodes of the LangGraph workflow.

    Attributes:
        messages (List[BaseMessage]): The history of messages in the conversation.
        `add_messages` ensures new messages are appended to the list, not overwritten.
    """
    messages: Annotated[List[BaseMessage], add_messages]