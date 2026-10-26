"""Portable opt-in browser test discovery; never downloads a browser or a package."""
import os
from pathlib import Path
import shutil
import sys
import unittest

def browser_executable():
    explicit = os.environ.get('WORKBENCH_CHROME')
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute() or not candidate.is_file():
            raise unittest.SkipTest('WORKBENCH_CHROME must name an existing absolute Chrome/Chromium executable')
        return candidate
    candidates = []
    if sys.platform == 'win32':
        for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            base = os.environ.get(variable)
            if base:
                candidates += [Path(base) / 'Google/Chrome/Application/chrome.exe', Path(base) / 'Chromium/Application/chrome.exe']
    elif sys.platform == 'darwin':
        candidates += [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'), Path('/Applications/Chromium.app/Contents/MacOS/Chromium')]
    for command in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            # Resolve executable aliases to the actual file accepted by the renderer.
            return candidate.resolve()
    raise unittest.SkipTest('Existing Chrome/Chromium unavailable; set WORKBENCH_CHROME to enable browser tests')

def require_browser():
    try:
        import playwright.sync_api
    except ImportError:
        raise unittest.SkipTest('Python Playwright unavailable; browser tests not run')
    return browser_executable()
