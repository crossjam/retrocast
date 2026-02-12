#!/usr/bin/env python3
"""Conditional type checking script that skips castchat files if dependencies aren't installed."""
import subprocess
import sys
import importlib.util


def has_castchat_deps():
    """Check if castchat dependencies are installed."""
    try:
        return (
            importlib.util.find_spec('chromadb') is not None and
            importlib.util.find_spec('pydantic_ai') is not None
        )
    except (ImportError, ValueError):
        return False


def main():
    """Run ty check, excluding castchat files if dependencies aren't installed."""
    if has_castchat_deps():
        # All dependencies available, check everything
        cmd = ['ty', 'check', 'src/']
        print("Castchat dependencies found. Checking all files...")
    else:
        # Castchat dependencies not available, exclude those files
        cmd = [
            'ty', 'check',
            '--exclude', 'src/retrocast/castchat_agent.py',
            '--exclude', 'src/retrocast/chromadb_manager.py',
            'src/'
        ]
        print("Castchat dependencies not installed. Excluding castchat files from type check...")
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
