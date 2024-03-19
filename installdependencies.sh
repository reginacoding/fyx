#!/bin/bash

# Install Python 3.9
sudo apt-get update
sudo apt-get install -y python3.9 python3.9-venv

# Create and activate a Python 3.9 virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install the openai library
pip3 install ./requirements.txt