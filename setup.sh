#!/bin/bash
# Setup script for Unix/Linux/Mac

echo "Setting up PARA Autopilot Backend..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp ../.env.example .env
    echo "Please edit .env with your actual credentials"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys and credentials"
echo "2. Run the SQL schema in backend/schema.sql in your Supabase project"
echo "3. Start the server: uvicorn main:app --reload"
echo ""
