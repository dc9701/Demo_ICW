# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
. .\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install common dependencies
pip install -r .\resources\requirements.txt

# Install Windows-specific packages
pip install dotenv json

# Install flake8 its plugins and testing packages
pip install -r .\resources\test_requirements.txt
