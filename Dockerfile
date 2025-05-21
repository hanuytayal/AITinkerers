# 1. Base Image
FROM python:3.9-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Environment variables
# Ensures Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED 1
# Set the port the app will run on
ENV PORT 8000

# 4. Copy Requirements
# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# 5. Install Dependencies
# --no-cache-dir reduces image size
# --upgrade pip ensures pip is up to date
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Application Code
# Copy the rest of the application files
COPY . .

# 7. Expose Port
# Expose the port the app runs on, as defined by ENV PORT
EXPOSE $PORT

# 8. Default Command
# Run Uvicorn server. 
# Use 0.0.0.0 to make it accessible from outside the container.
# --host 0.0.0.0 --port $PORT ensures it uses the environment variable for port.
# The default number of workers is 1. For production, you might increase this.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
