from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent

from lang.state.state import AgentState
from lang.tools.tools import all_tools
from config import llm

# --- A CUSTOM PROMPT FOR OUR AGENT ---
agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a powerful AI assistant. You can use tools to query a database or you can answer questions based on content from an uploaded file.

        - If the user's message includes text from a file (PDF, TXT, CSV), you MUST prioritize that content to answer their question.
        - If the user uploads an image, describe it or answer questions about it.
        - If the user asks to "list tables," use the `get_database_tables` tool.
        - If the request involves "export," "file," or "excel" for database information, use the `export_database_info_to_excel` tool.
        - For other database queries, use the `get_database_info` tool.
        - For general conversation, answer directly without using tools."""),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# --- AGENT EXECUTOR ---
agent_runnable = create_tool_calling_agent(llm, all_tools, agent_prompt)
agent_executor = AgentExecutor(agent=agent_runnable, tools=all_tools, verbose=True)


def agent_node(state: AgentState) -> dict:
    """
    Executes the agent with the current conversation state.

    Args:
        state (AgentState): The current state of the graph.

    Returns:
        A dictionary containing the agent's response messages.
    """
    print("--- [NODE] Executing Agent Node ---")
    response = agent_executor.invoke(state)
    return {"messages": [AIMessage(content=response["output"])]}