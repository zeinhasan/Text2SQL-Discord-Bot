from typing import List, TypedDict, Annotated, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Represents the state of our agent graph.

    Attributes:
        messages (List[BaseMessage]): The history of messages in the conversation.
        query_result (List[Dict[str, Any]] | None): The result from a SQL query execution.
        file_path (str | None): The path to a generated file, if any.
    """
    # `add_messages` ensures new messages are appended to the list, not overwritten.
    messages: Annotated[List[BaseMessage], add_messages]
    query_result: List[Dict[str, Any]] | None
    file_path: str | None