#!/bin/bash

# Start the FastAPI application with Uvicorn and redirect output to backend.log
nohup uvicorn app:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 & pid1=$!

# Start frontend development server
(cd frontend && nohup bun run dev) > frontend.log 2>&1 & pid2=$!

# Function to kill all child processes
kill_children() {
    echo "Killing all child processes..."
    kill -TERM $pid1 $pid2
}
trap kill_children EXIT
trap kill_children SIGINT
trap kill_children SIGTERM
trap kill_children SIGHUP
trap kill_children SIGQUIT

echo "Started process 1 with PID: $pid1"
echo "Started process 2 with PID: $pid2"

# Wait for both processes to complete
wait $pid1 $pid2

echo "Both processes have finished."
echo "Command 1 exit status: $?"
echo "Command 2 exit status: $?"
