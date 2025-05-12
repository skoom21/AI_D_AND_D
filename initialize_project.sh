#!/bin/bash
# Script to initialize the Text RPG project on Linux/macOS

echo "Checking for Python 3..."
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found."
    echo "Please install Python 3."
    exit 1
fi

PYTHON_EXE=$(command -v python3)
echo "Found Python 3 at: $PYTHON_EXE"

echo "Creating Python virtual environment (venv)..."
$PYTHON_EXE -m venv venv
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment."
    exit 1
fi

echo "Activating virtual environment and installing dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate

pip install --upgrade pip
pip install google-generativeai pygame python-dotenv
if [ $? -ne 0 ]; then
    echo "Failed to install Python packages."
    deactivate
    exit 1
fi

echo "Dependencies installed successfully."

# Prompt for API Key and save to .env file
read -rp "Please enter your Gemini API Key: " GEMINI_API_KEY

echo "Saving API key to .env file..."
echo "GEMINI_API_KEY=$GEMINI_API_KEY" > .env

# Deactivate environment
deactivate

echo
echo "Setup Complete!"
echo
echo "To activate the virtual environment in the future, run:"
echo "source venv/bin/activate"
echo
echo "Your Gemini API Key has been saved to the .env file."

exit 0
