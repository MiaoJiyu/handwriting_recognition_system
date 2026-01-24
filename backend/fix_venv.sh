#!/bin/bash
# Script to recreate venv with system Python instead of Nix Python

echo "=== 修复虚拟环境 ==="
echo ""

# Find system Python
find_system_python() {
    for python_cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            python_path=$(command -v "$python_cmd")
            if [[ "$python_path" != *"/nix-profile"* ]] && [[ "$python_path" != *"/.nix-profile"* ]]; then
                echo "$python_path"
                return 0
            fi
        fi
    done
    return 1
}

SYSTEM_PYTHON=$(find_system_python)

if [ -z "$SYSTEM_PYTHON" ]; then
    echo "错误: 未找到系统Python。请安装系统Python3。"
    exit 1
fi

echo "找到系统Python: $SYSTEM_PYTHON"
echo "Python版本: $($SYSTEM_PYTHON --version)"
echo ""

# Backup old venv
VENV_DIR="/opt/handwriting_recognition_system/venv"
if [ -d "$VENV_DIR" ]; then
    echo "备份现有虚拟环境..."
    mv "$VENV_DIR" "${VENV_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create new venv with system Python
echo "使用系统Python创建新的虚拟环境..."
cd /opt/handwriting_recognition_system
"$SYSTEM_PYTHON" -m venv venv

# Activate and upgrade pip
echo "升级pip..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install requirements
echo "安装依赖包..."
cd backend
pip install -r requirements.txt

echo ""
echo "✓ 虚拟环境已重新创建！"
echo "现在可以运行: ./run_server.sh 或 uvicorn app.main:app --reload"
