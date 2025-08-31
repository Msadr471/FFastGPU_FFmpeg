# hook-setuptools.py
# Fix for missing setuptools._vendor.packaging.licenses module

hiddenimports = []

# This module was removed and doesn't exist anymore
# We explicitly tell PyInstaller to not look for it
excludedimports = ['setuptools._vendor.packaging.licenses']