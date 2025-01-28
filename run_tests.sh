#!/bin/bash

# Kill any existing Python processes
echo "Killing existing Python processes..."
pkill -f "python3 file_agent.py"
sleep 2

# Start the API server in the background
echo "Starting API server..."
python3 file_agent.py &
API_PID=$!

# Wait for the server to start
echo "Waiting for server to start..."
sleep 3

# Run the tests
echo "Running tests..."
python3 validation_test.py

# Kill the API server
echo "Cleaning up..."
kill $API_PID

echo "Done!"
