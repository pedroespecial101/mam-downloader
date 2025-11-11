#!/bin/bash
# Setup script for MAM Downloader with libtorrent support

echo "=================================="
echo "MAM Downloader Setup Script"
echo "=================================="
echo ""

# Detect OS
OS=$(uname -s)
echo "Detected OS: $OS"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install libtorrent based on OS
if [ "$OS" = "Darwin" ]; then
    echo "Installing dependencies for macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        echo "❌ Homebrew not found. Please install it first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "Installing libtorrent-rasterbar via Homebrew..."
    brew install libtorrent-rasterbar
    
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
    
elif [ "$OS" = "Linux" ]; then
    echo "Installing dependencies for Linux..."
    
    # Detect package manager
    if command_exists apt-get; then
        echo "Using apt-get..."
        sudo apt-get update
        sudo apt-get install -y python3-libtorrent
        pip3 install -r requirements.txt
        
    elif command_exists yum; then
        echo "Using yum..."
        sudo yum install -y rb_libtorrent-python3
        pip3 install -r requirements.txt
        
    else
        echo "⚠️  Could not detect package manager."
        echo "   Trying pip installation..."
        pip3 install -r requirements.txt
    fi
    
else
    echo "⚠️  Unsupported OS: $OS"
    echo "   Trying pip installation..."
    pip3 install -r requirements.txt
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit config.py and set your MAM_ID"
echo "2. Run: python3 test_modules.py"
echo "3. Try: python3 main_new.py --help"
echo ""
