#!/bin/bash

# Install Python 3.12
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv

# Create and activate a Python 3.12 virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install the openai library
pip install ./requirements.txt