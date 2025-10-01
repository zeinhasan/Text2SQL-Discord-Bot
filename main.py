import discord
from discord.ext import commands
import os
import asyncio
from config import DISCORD_TOKEN
from lang.graph.graph import app
from lang.tools.file_processor import process_uploaded_file
from langchain_core.messages import HumanMessage
from utils import find_excel_path_in_response, find_image_path_in_response

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

    **How to interact with me:**
    - Mention me (`@botzein`) with your question.
    - To generate an image, mention me, describe the image you want, and attach a reference image if needed.
    - Example: `@botzein Create a logo for a coffee shop, using this color palette.` (with an image attached).

    **What I can do:**
    - Answer questions based on the connected database.
    - Export data from the database to an Excel file.
    - Read and understand content from `.txt`, `.pdf`, `.csv`, and `.xlsx` files.
    - Generate or modify images based on your text prompts and uploaded images.
    """
    await ctx.send(help_text)

@bot.event
async def on_message(message):
    """
    Handles incoming messages, processing mentions and attachments.
    """
    # Ignore messages sent by the bot itself to prevent loops.
    if message.author == bot.user:
        return

    # Process messages where the bot is mentioned.
    if bot.user.mentioned_in(message):
        # Extract the user's message, removing the bot's mention.
        user_message = message.content.replace(f"<@{bot.user.id}>", "").strip()
        print(f"--- [ON_MESSAGE] Received mention from {message.author}: '{user_message}' ---")

        # Create a new thread for the conversation to keep the channel clean.
        thread = await message.channel.create_thread(
            name=f"Responding to {message.author.display_name}",
            type=discord.ChannelType.public_thread
        )
        
        # Send an initial status message to acknowledge the request.
        status_message = await thread.send("Processing your request...")

        # Initialize the content to be sent to the language model.
        final_user_content = user_message

        try:
            # --- Attachment Handling ---
            if message.attachments:
                print(f"--- [ON_MESSAGE] Found {len(message.attachments)} attachment(s). ---")
                attachment = message.attachments[0]
                file_path = os.path.join("uploads", attachment.filename)
                await attachment.save(file_path)
                print(f"--- [ON_MESSAGE] Saved attachment to {file_path} ---")

                # Process the uploaded file to extract its content.
                processed_file = process_uploaded_file(file_path)

                # Prepare the input for the language model based on the file type.
                if processed_file['type'] == 'image':
                    image_data = processed_file['content']
                    final_user_content = [
                        {"type": "text", "text": user_message},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                    print("--- [ON_MESSAGE] Prepared multimodal input for LLM (image). ---")
                else:
                    # For text-based files, prepend the content to the user's message.
                    file_text_content = processed_file['content']
                    final_user_content = f"File Content:\n{file_text_content}\n\n---\n\nUser Question: {user_message}"
                    print("--- [ON_MESSAGE] Prepended text file content to user message. ---")

            # --- LangGraph Invocation ---
            # Prepare the final input for the LangGraph agent.
            inputs = {"messages": [HumanMessage(content=final_user_content)]}
            
            print("--- [ON_MESSAGE] Invoking LangGraph with prepared inputs... ---")
            # Run the synchronous LangGraph agent in a separate thread to avoid blocking.
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(None, lambda: app.invoke(inputs))
            
            # Extract the final response from the agent's state.
            print("--- [ON_MESSAGE] LangGraph invocation finished. Processing final state. ---")
            response_content = str(final_state['messages'][-1].content).strip()

            # --- Response Handling ---
            # Check if the response contains a path to an Excel or image file.
            excel_file_path = find_excel_path_in_response(response_content)
            image_file_path = find_image_path_in_response(response_content)

            if excel_file_path:
                # If an Excel file was generated, send it as an attachment.
                print(f"--- [ON_MESSAGE] Sending Excel file: {excel_file_path} ---")
                await status_message.edit(content="Here is the Excel file you requested:")
                await thread.send(file=discord.File(excel_file_path))
            elif image_file_path:
                # If an image file was generated, send it as an attachment.
                print(f"--- [ON_MESSAGE] Sending Image file: {image_file_path} ---")
                await status_message.edit(content="Here is your generated image:")
                await thread.send(file=discord.File(image_file_path))
            else:
                # Otherwise, send the text-based response.
                print(f"--- [ON_MESSAGE] No file path found. Sending text response. ---")
                await status_message.edit(content=response_content)

        except Exception as e:
            # --- Error Handling ---
            print(f"--- [ON_MESSAGE_ERROR] An unexpected error occurred: {e} ---")
            await status_message.edit(content=f"An unexpected error occurred. Please check the logs.")

# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("--- [FATAL_ERROR] DISCORD_TOKEN is not set. Please check your .env file. ---")
    else:
        print("--- [MAIN] Starting bot... ---")
        bot.run(DISCORD_TOKEN)