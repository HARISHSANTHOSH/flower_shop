#!/bin/bash

# Activate virtualenv
source /home/harish/venv/bin/activate

# Start Celery worker
celery -A flowerproject worker --loglevel=info &

# Start Celery beat


echo "Celery worker and beat started!"
