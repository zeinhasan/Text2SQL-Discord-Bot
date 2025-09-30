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
    """Event handler for when the bot has successfully connected to Discord."""
    print(f"--- BOT IS ONLINE ---")
    print(f"Logged in as: {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("---------------------------------")

@bot.command(name="helpme")
async def help_command(ctx):
    """
    Displays a help message with instructions on how to use the bot.
    """
    print(f"--- [COMMAND] !helpme executed by {ctx.author} ---")
    help_text = """
    **Hello! I am a Text-to-SQL AI Bot.**
    
    To ask me to get data from the database, simply **@mention me** followed by your request.
    
    **Examples:**
    - `@YourBotName show me all users from the customers table`
    - `@YourBotName what is the total sales for the last month?`
    - `@YourBotName show me the top 5 products and export the result to excel`
    
    **Available Commands:**
    - `!helpme` - Shows this help message.
    """
    await ctx.send(help_text)

# --- FINAL, MOST ROBUST HELPER FUNCTION TO FIND FILE PATH ---
def find_file_path_in_response(response_text: str) -> str | None:
    """
    Uses a robust regular expression to find a valid .xlsx file path in the response text.
    It normalizes slashes to handle different OS path formats.
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
    Event handler for when a message is sent in any channel the bot can see.
    """
    await bot.process_commands(message)

    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        user_message = message.content.replace(f'<@!{bot.user.id}>', '').strip()
        print(f"\n--- [ON_MESSAGE] Received mention from {message.author}: '{user_message}' ---")
        
        if not user_message:
            await message.channel.send("Ya, ada yang bisa saya bantu?")
            return

        thread = await message.channel.send(f"⏳ Memproses permintaan Anda: *'{user_message}'*...")
        
        inputs = {"messages": [HumanMessage(content=user_message)]}

        try:
            loop = asyncio.get_running_loop()
            final_state = await loop.run_in_executor(None, lambda: app.invoke(inputs))
            
            print("--- [ON_MESSAGE] LangGraph invocation finished. Processing final state. ---")
            last_message = final_state['messages'][-1]
            response_content = str(last_message.content).strip()

            file_path = find_file_path_in_response(response_content)

            if file_path:
                print(f"--- [ON_MESSAGE] Extracted file path from response: {file_path} ---")
                await thread.edit(content="Tentu, ini file Excel yang Anda minta:")
                await message.channel.send(file=discord.File(file_path))
            else:
                print(f"--- [ON_MESSAGE] No file path found. Sending text response. ---")
                if len(response_content) > 1900:
                    summary_prompt = f"Please summarize the following text into a short, readable response for Discord: {response_content}"
                    print("--- [ON_MESSAGE] Response is too long. Asking LLM for a summary. ---")
                    
                    summary_response = await loop.run_in_executor(None, lambda: llm.invoke(summary_prompt))
                    
                    await thread.edit(content=summary_response.content)
                else:
                    await thread.edit(content=response_content)

        except Exception as e:
            error_str = str(e).lower()
            print(f"--- [ON_MESSAGE_ERROR] An error occurred: {e} ---")
            
            if "timeout" in error_str or "deadline exceeded" in error_str or "wait" in error_str:
                 await thread.edit(content=f"Maaf, permintaan ke model AI timeout. Kemungkinan ini masalah jaringan sementara. Silakan coba lagi sesaat lagi.")
            else:
                 await thread.edit(content=f"Maaf, terjadi kesalahan tak terduga saat memproses permintaan Anda.")

# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("--- FATAL_ERROR: DISCORD_TOKEN is not set in the .env file. Exiting. ---")
    else:
        print("--- [MAIN] Starting bot... ---")
        bot.run(DISCORD_TOKEN)