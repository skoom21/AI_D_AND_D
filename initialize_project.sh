#!/bin/bash

# Navigate to the project directory (if the script is not already there)
# SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# cd "$SCRIPT_DIR"

# Define the virtual environment directory name
VENV_DIR=".venv"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install Python 3 and try again."
    exit 1
fi

# Create a virtual environment
if [ ! -d "$VENV_DIR" ]
then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please check your Python installation."
        exit 1
    fi
else
    echo "Virtual environment '$VENV_DIR' already exists."
fi

# Activate the virtual environment
# The activation script path differs between OSes
if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    source "$VENV_DIR/bin/activate"
elif [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source "$VENV_DIR/Scripts/activate"
else
    echo "Unsupported OS for venv activation. Please activate manually: source $VENV_DIR/bin/activate or $VENV_DIR\Scripts\activate"
    exit 1
fi

echo "Virtual environment activated."

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]
then
    echo "Installing dependencies from requirements.txt..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please check requirements.txt and your internet connection."
        # Deactivate venv before exiting on error
        deactivate
        exit 1
    fi
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

# Run the main application
echo "Running main.py..."
python3 main.py

# Deactivate the virtual environment upon exiting the script (optional)
# echo "Deactivating virtual environment..."
# deactivate

echo "Script finished."
