from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent

from lang.state.state import AgentState
from lang.tools.tools import all_tools
from config import llm

# --- A CUSTOM PROMPT FOR OUR AGENT ---
agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a powerful AI assistant that can help users with their questions and use tools to get the job done.

        - If the user asks to "list tables" or a similar question, you must use the `list_database_tables` tool.
        - If the user's message contains words like "export," "file," "excel," or "spreadsheet," you must use the `query_database_and_export_to_excel` tool.
        - For all other requests that require data from a specific table, you must use the `query_database_and_get_text_result` tool.
        - If the user is just saying hello, answer directly.

        Pass the user's entire, original question into the `question` parameter of the chosen tool if needed."""),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# --- A SINGLE AGENT EXECUTOR  ---
agent_runnable = create_tool_calling_agent(llm, all_tools, agent_prompt)
agent_executor = AgentExecutor(agent=agent_runnable, tools=all_tools, verbose=True)


def agent_node(state: AgentState) -> dict:
    """
    This node is responsible for executing the agent. It takes the current state of the conversation as input and returns a dictionary with the agent's response.
    """
    print("--- NODE: EXECUTING AGENT ---")
    response = agent_executor.invoke(state)
    return {"messages": [AIMessage(content=response["output"])]}