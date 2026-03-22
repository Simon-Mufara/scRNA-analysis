#!/bin/bash
# Start Streamlit with proper configuration

cd /users/simon/python_lessons/scRNA_Explorer

# Kill any existing Streamlit processes
pkill -f "streamlit run"
sleep 1

# Clear Streamlit cache for fresh start
rm -rf ~/.streamlit/cache

# Start Streamlit
echo "Starting Streamlit on 0.0.0.0:8501..."
streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --logger.level=info \
  --client.showErrorDetails=true

