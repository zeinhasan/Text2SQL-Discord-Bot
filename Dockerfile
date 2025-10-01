# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Set environment variables from .env file (or pass them during `docker run`)
# Note: The .env file itself is not copied for security reasons.
# You should pass environment variables using `docker run --env-file .env`
ENV DISCORD_TOKEN=""
ENV DB_HOST=""
ENV DB_USER=""
ENV DB_PASSWORD=""
ENV DB_NAME=""
ENV GOOGLE_API_KEY=""
ENV GEMINI_MODEL_NAME="gemini-1.5-flash-latest"

# Run main.py when the container launches
CMD ["python", "main.py"]