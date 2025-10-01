import discord
from discord.ext import commands
import os
import asyncio
from utils import find_excel_path_in_response, find_image_path_in_response
from config import DISCORD_TOKEN, llm
from lang.graph.graph import app
from lang.tools.file_processor import process_uploaded_file
from langchain_core.messages import HumanMessage

# --- Bot Initialization ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Handles the event when the bot successfully connects to Discord.
    """
    print(f"------- BOT IS ONLINE -------")
    print(f"Logged in as: {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        print("--- [MAIN] Created 'uploads' directory. ---")
    if not os.path.exists("output"):
        os.makedirs("output")
        print("--- [MAIN] Created 'output' directory. ---")
    print("-----------------------------")

@bot.command(name="helpme")
async def help_command(ctx):
    """
    Displays a help message with instructions on how to use the bot.
    """
    print(f"--- [COMMAND] !help executed by {ctx.author} ---")
    help_text = """
    **Hello! I am an AI assistant.**

    You can ask me questions about data in the database, about files you upload, or request image generation.

    **Database Queries:**
    - `@YourBotName show me all users from the customers table`
    - `@YourBotName what is the total sales for the last month?`
    - `@YourBotName show me the top 5 products and export the result to excel`

    **File-based Questions:**
    - Upload a file (PDF, TXT, CSV, XLSX, PNG, JPG) and **@mention me** with your question in the comment.
    - Example: `(upload a sales_report.pdf) @YourBotName what were the total profits in Q3?`

    **Image Generation:**
    - `@YourBotName create an image of a cat playing a guitar`
    - `@YourBotName modify this image (upload image) to make the cat wear a hat`
    """
    await ctx.send(help_text)

@bot.event
async def on_message(message: discord.Message):
    """
    Handles incoming messages and processes them if the bot is mentioned.
    """
    await bot.process_commands(message)

    if message.author == bot.user or not bot.user.mentioned_in(message):
        return

    user_message = message.content.replace(f'<@!{bot.user.id}>', '').strip()
    print(f"\n--- [ON_MESSAGE] Received mention from {message.author}: '{user_message}' ---")
    
    final_user_content = user_message
    
    if message.attachments:
        print(f"--- [ON_MESSAGE] Found {len(message.attachments)} attachment(s). ---")
        attachment = message.attachments[0]
        file_path = os.path.join("uploads", attachment.filename)
        await attachment.save(file_path)
        print(f"--- [ON_MESSAGE] Saved attachment to {file_path} ---")
        
        processed_file = process_uploaded_file(file_path)
        
        if processed_file['type'] == 'image':
            image_data = processed_file['content']
            final_user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_data}"}
            ]
            print("--- [ON_MESSAGE] Prepared multimodal input for LLM (image). ---")
        else:
            file_text_content = processed_file['content']
            final_user_content = f"{file_text_content}\n\n---\n\nUser Question: {user_message}"
            print("--- [ON_MESSAGE] Prepended text file content to user message. ---")

    if not user_message and not message.attachments:
        await message.channel.send("How can I help you?")
        return

    thread = await message.channel.send(f"⏳ Processing your request...")
    
    inputs = {"messages": [HumanMessage(content=final_user_content)]}

    try:
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(None, lambda: app.invoke(inputs))
        
        print("--- [ON_MESSAGE] LangGraph invocation finished. Processing final state. ---")
        response_content = str(final_state['messages'][-1].content).strip()

        excel_file_path = find_excel_path_in_response(response_content)
        image_file_path = find_image_path_in_response(response_content)

        if excel_file_path:
            print(f"--- [ON_MESSAGE] Sending Excel file: {excel_file_path} ---")
            await thread.edit(content="Here is the Excel file you requested:")
            await message.channel.send(file=discord.File(excel_file_path))
        elif image_file_path:
            print(f"--- [ON_MESSAGE] Sending Image file: {image_file_path} ---")
            await thread.edit(content="Here is your generated image:")
            await message.channel.send(file=discord.File(image_file_path))
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
        print(f"--- [ON_MESSAGE_ERROR] An unexpected error occurred: {e} ---")
        await thread.edit(content=f"An unexpected error occurred. Please check the logs.")

# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("--- [FATAL_ERROR] DISCORD_TOKEN is not set in the .env file. ---")
    else:
        print("--- [MAIN] Starting bot... ---")
        bot.run(DISCORD_TOKEN)