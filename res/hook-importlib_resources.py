# hook-importlib_resources.py
# Fix for missing importlib_resources.trees module

hiddenimports = []

# This module was removed in Python 3.9+ and doesn't exist anymore
# We explicitly tell PyInstaller to not look for it
excludedimports = ['importlib_resources.trees']