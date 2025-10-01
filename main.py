import discord
from discord.ext import commands
import json
import os
import asyncio
import re

from config import DISCORD_TOKEN, llm
from lang.graph.graph import app
from langchain_core.messages import HumanMessage

# --- Bot Initialization ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Handles the event when the bot successfully connects to Discord.
    This function prints a confirmation message to the console, including the bot's username and ID.
    """
    print(f"------- BOT IS ONLINE -------")
    print(f"Logged in as: {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("-----------------------------")

@bot.command(name="helpme")
async def help_command(ctx):
    """
    Displays a help message with instructions on how to use the bot.
    
    This command provides users with a clear guide on how to interact with the bot,
    including the correct syntax for asking questions and a list of available commands.
    """
    print(f"--- [COMMAND] !help executed by {ctx.author} ---")
    help_text = """
    **Hello! I am a Text-to-SQL AI Bot.**

    To get data from the database, simply **@mention me** followed by your request.

    **Examples:**
    - `@YourBotName show me all users from the customers table`
    - `@YourBotName what is the total sales for the last month?`
    - `@YourBotName show me the top 5 products and export the result to excel`

    **Available Commands:**
    - `!help` - Shows this help message.
    """
    await ctx.send(help_text)

# --- Helper Function to Find File Path ---
def find_file_path_in_response(response_text: str) -> str | None:
    """
    Searches for and validates a file path from the AI's response text.

    This function uses a regular expression to find potential .xlsx file paths,
    normalizes them for the current operating system, and verifies that the file exists.
    
    Args:
        response_text: The text from which to extract the file path.

    Returns:
        The validated, OS-specific file path if found and it exists, otherwise None.
    """
    print(f"--- [HELPER] Searching for path in: '{response_text}' ---")
    
    # Normalize all backslashes to forward slashes for consistent matching
    normalized_text = response_text.replace('\\', '/')
    
    # This regex looks for a full path (e.g., C:/...) or a relative path (e.g., output/...)
    # that ends in .xlsx
    match = re.search(r"([a-zA-Z]:/.*?\.xlsx|output/.*?\.xlsx)", normalized_text)
    
    if match:
        # The first group in the match is our path with forward slashes
        path_with_forward_slashes = match.group(1).strip(".,'\"()")
        
        # Convert the path to the correct format for the current operating system (e.g., D:\...)
        os_specific_path = os.path.normpath(path_with_forward_slashes)
        
        print(f"--- [HELPER] Regex found potential path: {os_specific_path} ---")
        
        # Verify that the extracted path actually exists on the disk
        if os.path.exists(os_specific_path):
            print(f"--- [HELPER] Path confirmed to exist. ---")
            return os_specific_path
        else:
            print(f"--- [HELPER] Path found by regex does NOT exist: {os_specific_path} ---")
            
    print(f"--- [HELPER] No valid .xlsx file path found in response. ---")
    return None

# --- Main Event Handler for AI Responses ---
@bot.event
async def on_message(message: discord.Message):
    """
    Handles incoming messages, processing them if the bot is mentioned.

    This function checks for bot mentions, extracts the user's query,
    and sends it to the LangGraph application for processing. It then handles
    the response, sending either a text message or a file.
    
    Args:
        message: The discord.Message object representing the message sent.
    """
    # This allows the bot to still process commands like !help
    await bot.process_commands(message)

    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Check if the bot was mentioned in the message
    if bot.user.mentioned_in(message):
        # Extract the user's message, removing the bot mention
        user_message = message.content.replace(f'<@!{bot.user.id}>', '').strip()
        print(f"\n--- [ON_MESSAGE] Received mention from {message.author}: '{user_message}' ---")
        
        # If the message is empty after removing the mention, ask for clarification
        if not user_message:
            await message.channel.send("Yes, how can I help you?")
            return

        # Send an initial "processing" message
        thread = await message.channel.send(f"⏳ Processing your request: *'{user_message}'*...")
        
        # Prepare the input for the LangGraph application
        inputs = {"messages": [HumanMessage(content=user_message)]}

        try:
            # Run the synchronous LangGraph invocation in a separate thread
            loop = asyncio.get_running_loop()
            final_state = await loop.run_in_executor(None, lambda: app.invoke(inputs))
            
            print("--- [ON_MESSAGE] LangGraph invocation finished. Processing final state. ---")
            last_message = final_state['messages'][-1]
            response_content = str(last_message.content).strip()

            # Check if the response contains a file path
            file_path = find_file_path_in_response(response_content)

            if file_path:
                # If a file path is found, send the file
                print(f"--- [ON_MESSAGE] Extracted file path from response: {file_path} ---")
                await thread.edit(content="Of course, here is the Excel file you requested:")
                await message.channel.send(file=discord.File(file_path))
            else:
                # If no file path is found, send the text response
                print(f"--- [ON_MESSAGE] No file path found. Sending text response. ---")
                if len(response_content) > 1900:
                    # If the response is too long for Discord, summarize it
                    summary_prompt = f"Please summarize the following text into a short, readable response for Discord: {response_content}"
                    print("--- [ON_MESSAGE] Response is too long. Asking LLM for a summary. ---")
                    
                    summary_response = await loop.run_in_executor(None, lambda: llm.invoke(summary_prompt))
                    
                    await thread.edit(content=summary_response.content)
                else:
                    # Otherwise, send the response as is
                    await thread.edit(content=response_content)

        except Exception as e:
            error_str = str(e).lower()
            print(f"--- [ON_MESSAGE_ERROR] An error occurred: {e} ---")
            
            # Provide a user-friendly error message for common issues
            if "timeout" in error_str or "deadline exceeded" in error_str or "wait" in error_str:
                 await thread.edit(content=f"Sorry, the request to the AI model timed out. This might be a temporary network issue. Please try again in a moment.")
            else:
                 await thread.edit(content=f"Sorry, an unexpected error occurred while processing your request.")

# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("--- FATAL_ERROR: DISCORD_TOKEN is not set in the .env file. Exiting. ---")
    else:
        print("--- [MAIN] Starting bot... ---")
        bot.run(DISCORD_TOKEN)