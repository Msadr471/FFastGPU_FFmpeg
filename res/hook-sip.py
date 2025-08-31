# hook-sip.py
# Fix for sip module warnings in PyQt5

from PyInstaller.utils.hooks import collect_submodules

# In newer PyQt5 versions, sip functionality is integrated into PyQt5 itself
# We collect all sip-related modules from PyQt5
hiddenimports = collect_submodules('PyQt5', filter=lambda name: 'sip' in name)

# Also try to import sip directly and add it if available
try:
    from PyQt5 import sip
    hiddenimports.append('sip')
except ImportError:
    # If sip is not available as a separate module, that's fine
    # It's integrated into PyQt5 in newer versions
    pass

# Add PyQt5.sip explicitly
hiddenimports.append('PyQt5.sip')