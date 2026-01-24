#!/bin/bash
# Startup script for the backend server with proper library paths and Python selection

# Find system Python (not Nix-managed)
find_system_python() {
    # Common system Python locations
    for python_cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            python_path=$(command -v "$python_cmd")
            # Check if it's NOT from Nix
            if [[ "$python_path" != *"/nix-profile"* ]] && [[ "$python_path" != *"/.nix-profile"* ]]; then
                echo "$python_path"
                return 0
            fi
        fi
    done
    return 1
}

# Try to use system Python if available
SYSTEM_PYTHON=$(find_system_python)

# Set library paths for system libraries
export LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib/gcc/x86_64-linux-gnu/13:${LD_LIBRARY_PATH}

# Change to backend directory
cd /opt/handwriting_recognition_system/backend

# If we found a system Python, use it directly with the venv's packages
if [ -n "$SYSTEM_PYTHON" ]; then
    echo "Using system Python: $SYSTEM_PYTHON"
    # Use system Python with venv's site-packages
    export PYTHONPATH="/opt/handwriting_recognition_system/venv/lib/python3.13/site-packages:$PYTHONPATH"
    exec "$SYSTEM_PYTHON" -m uvicorn app.main:app --reload
else
    # Fallback: try to use venv Python with Nix workaround
    echo "Warning: Using Nix Python, may have compatibility issues"
    # Unset Nix-specific environment variables that might interfere
    unset NIX_PATH
    unset NIX_PROFILES
    
    # Activate virtual environment if it exists
    if [ -f "/opt/handwriting_recognition_system/venv/bin/activate" ]; then
        source /opt/handwriting_recognition_system/venv/bin/activate
    fi
    
    # Run uvicorn
    exec uvicorn app.main:app --reload
fi
