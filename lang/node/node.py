from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent

from lang.state.state import AgentState
from lang.tools.tools import all_tools, generate_image
from config import llm

# --- Agent Prompt ---
# This prompt template is used to instruct the agent on how to behave.
agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are a powerful AI assistant. Your primary function is to answer questions using the provided tools. Follow these rules without deviation:
        1.  **Default to Displaying Data**: For any request to "get", "show", "find", "view", or "extract" data, you MUST use the `query_database` tool to display the results directly in the chat.
        2.  **Strict Export Condition**: You are ONLY allowed to use the `export_to_excel` tool if the user's message contains the specific words 'export' or 'excel'.
        3.  **Exporting Rule**: When you use the `export_to_excel` tool, you MUST provide the `table_name` argument. You will extract this table name from the SQL query you generate. The tool will handle filename creation automatically. Do NOT attempt to create a filename yourself.
        4.  **Handle File Paths**: When a tool successfully creates a file (Excel or image), it will return a file path. Your final answer to the user MUST include this full, unmodified file path.
        """),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# --- Agent Executor ---
# This creates the agent executor by combining the LLM, tools, and prompt.
agent_runnable = create_tool_calling_agent(llm, all_tools, agent_prompt)
agent_executor = AgentExecutor(agent=agent_runnable, tools=all_tools, verbose=True)


def agent_node(state: AgentState) -> dict:
    """
    The primary agent node that handles database queries, file Q&A, and general chat.
    """
    print("--- [NODE] Executing General Agent Node ---")
    response = agent_executor.invoke(state)
    return {"messages": [AIMessage(content=response["output"])]}


def generate_image_node(state: AgentState) -> dict:
    """
A dedicated node that directly calls the image generation tool.
    """
    print("--- [NODE] Executing Dedicated Image Generation Node ---")
    last_message = state["messages"][-1]
    prompt = ""
    base64_image_data = None

    # Multi modal mode
    if isinstance(last_message.content, list):
        for part in last_message.content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    prompt = part.get("text", "")
                elif part.get("type") == "image_url":
                    image_uri = part.get("image_url", {}).get("url", "")
                    if "base64," in image_uri:
                        base64_image_data = image_uri.split(',')[-1]

    elif isinstance(last_message.content, str):
        print("--- [NODE] Processing text-only image request. ---")
        prompt = last_message.content
    
    if not prompt:
        error_message = "A text prompt is required to generate an image. For example: 'create a photo of a cat'."
        print(f"--- [NODE_ERROR] {error_message} ---")
        return {"messages": [AIMessage(content=error_message)]}
    
    print(f"--- [NODE] Calling image tool with prompt: '{prompt}' ---")
    result = generate_image.invoke({
        "prompt": prompt,
        "base64_image_data": base64_image_data
    })
    
    return {"messages": [AIMessage(content=result)]}