#!/bin/bash
# Quick workaround: Run server using system Python with venv packages

# Find system Python
for python_cmd in /usr/bin/python3.13 /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10 /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$python_cmd" ] && [[ "$python_cmd" != *"/nix-profile"* ]]; then
        SYSTEM_PYTHON="$python_cmd"
        break
    fi
done

if [ -z "$SYSTEM_PYTHON" ]; then
    echo "错误: 未找到系统Python。尝试使用: which python3"
    which python3
    exit 1
fi

echo "使用系统Python: $SYSTEM_PYTHON"

# Set library paths
export LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib/gcc/x86_64-linux-gnu/13:${LD_LIBRARY_PATH}

# Use venv's site-packages
VENV_SITE_PACKAGES="/opt/handwriting_recognition_system/venv/lib/python3.13/site-packages"
if [ ! -d "$VENV_SITE_PACKAGES" ]; then
    # Try to find the actual Python version in venv
    VENV_SITE_PACKAGES=$(find /opt/handwriting_recognition_system/venv/lib -name "site-packages" -type d | head -1)
fi

if [ -d "$VENV_SITE_PACKAGES" ]; then
    export PYTHONPATH="$VENV_SITE_PACKAGES:$PYTHONPATH"
    echo "使用虚拟环境的包: $VENV_SITE_PACKAGES"
else
    echo "警告: 未找到虚拟环境的site-packages目录"
fi

# Change to backend directory
cd /opt/handwriting_recognition_system/backend

# Run uvicorn with system Python
exec "$SYSTEM_PYTHON" -m uvicorn app.main:app --reload
