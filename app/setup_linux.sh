#!/bin/bash

# Script to setup Linux desktop support for Flutter

# Enable Linux desktop
flutter config --enable-linux-desktop

# Make sure required packages are installed
which apt-get > /dev/null && {
  echo "Installing Linux dependencies with apt-get..."
  sudo apt-get update
  sudo apt-get install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev
}

# Create Linux desktop files if they don't exist
if [ ! -d "linux" ]; then
  echo "Creating Linux desktop project files..."
  flutter create --platforms=linux .
fi

echo "Linux desktop setup complete!" 