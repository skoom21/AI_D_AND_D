@echo off
REM Batch script to initialize the Text RPG project on Windows


echo Creating Python virtual environment (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment.
    goto :eof
)

echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat

pip install --upgrade pip
pip install google-generativeai pygame python-dotenv
if %errorlevel% neq 0 (
    echo Failed to install Python packages.
    deactivate
    goto :eof
)

echo Dependencies installed successfully.

REM Prompt for API Key and save to .env file
set /p GEMINI_API_KEY="Please enter your Gemini API Key: "

echo Saving API key to .env file...
(echo GEMINI_API_KEY=%GEMINI_API_KEY%) > .env

REM Deactivate is usually automatic when script ends, but call it for clarity
call deactivate

echo.
echo Setup Complete!
echo.
echo To activate the virtual environment in the future, run:
echo venv\Scripts\activate.bat
echo.
echo Your Gemini API Key has been saved to the .env file.

goto :eof 
