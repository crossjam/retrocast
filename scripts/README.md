# Scripts Directory

This directory contains helper scripts for the retrocast project.

## check_types.py

A conditional type checking script that intelligently handles optional dependencies.

**Purpose**: The `poe type` task uses this script to run `ty` type checker on source files. 
When the castchat extra dependencies (`chromadb` and `pydantic-ai`) are not installed, 
the script automatically excludes the castchat-related files from type checking.

**Behavior**:
- If castchat dependencies are installed: Checks all files in `src/`
- If castchat dependencies are NOT installed: Checks all files except:
  - `src/retrocast/castchat_agent.py`
  - `src/retrocast/chromadb_manager.py`

**Usage**:
```bash
# Via poe task (recommended)
poe type

# Direct execution
python scripts/check_types.py
```

This allows developers to run type checking without requiring optional dependencies to be installed.
