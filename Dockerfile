FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for markitdown
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for files
RUN mkdir -p test_files markdown_results

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "file_agent:app", "--host", "0.0.0.0", "--port", "8001"]
