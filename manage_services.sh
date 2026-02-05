#!/bin/bash
# 字迹识别系统服务管理脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
BACKEND_VENV_PATH=""
INFERENCE_VENV_PATH=""
USE_VENV=false

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用sudo运行此脚本${NC}"
    exit 1
fi

# 配置 venv 路径
configure_venv() {
    echo ""
    echo -e "${GREEN}=================================="
    echo "  配置虚拟环境 (venv)"
    echo -e "==================================${NC}"
    read -p "是否使用虚拟环境？(y/n): " use_venv

    if [ "$use_venv" = "y" ] || [ "$use_venv" = "Y" ]; then
        USE_VENV=true
        echo ""

        # 后端 venv 路径
        while true; do
            read -p "请输入后端 venv 路径 (默认: /opt/handwriting_recognition_system/venv): " backend_path
            backend_path=${backend_path:-/opt/handwriting_recognition_system/venv}

            if [ -d "$backend_path" ] && [ -f "$backend_path/bin/activate" ]; then
                BACKEND_VENV_PATH="$backend_path"
                echo -e "${GREEN}✓ 后端 venv 路径: $BACKEND_VENV_PATH${NC}"
                break
            else
                echo -e "${RED}错误：路径不存在或不是有效的 venv 目录${NC}"
            fi
        done

        echo ""

        # 推理服务 venv 路径
        while true; do
            read -p "请输入推理服务 venv 路径 (默认: /opt/handwriting_recognition_system/venv): " inference_path
            inference_path=${inference_path:-/opt/handwriting_recognition_system/venv}

            if [ -d "$inference_path" ] && [ -f "$inference_path/bin/activate" ]; then
                INFERENCE_VENV_PATH="$inference_path"
                echo -e "${GREEN}✓ 推理服务 venv 路径: $INFERENCE_VENV_PATH${NC}"
                break
            else
                echo -e "${RED}错误：路径不存在或不是有效的 venv 目录${NC}"
            fi
        done

        echo ""
        echo -e "${GREEN}配置完成！${NC}"
    else
        USE_VENV=false
        echo -e "${YELLOW}将使用系统 Python 环境${NC}"
    fi
}

# 显示菜单
show_menu() {
    echo -e "${GREEN}=================================="
    echo "  字迹识别系统服务管理"
    echo -e "==================================${NC}"
    echo "1. 启动所有服务"
    echo "2. 停止所有服务"
    echo "3. 重启所有服务"
    echo "4. 查看服务状态"
    echo "5. 查看后端日志"
    echo "6. 查看推理服务日志"
    echo "7. 重新加载配置（不重启服务）"
    echo "8. 启用开机自启"
    echo "9. 禁用开机自启"
    echo "10. 重新创建 service 文件"
    echo "11. 配置 venv 路径"
    echo "0. 退出"

    # 显示当前 venv 配置状态
    if [ "$USE_VENV" = true ]; then
        echo ""
        echo -e "${YELLOW}[当前配置]${NC}"
        [ -n "$BACKEND_VENV_PATH" ] && echo -e "  后端 venv: $BACKEND_VENV_PATH"
        [ -n "$INFERENCE_VENV_PATH" ] && echo -e "  推理 venv: $INFERENCE_VENV_PATH"
    fi

    echo -e "${GREEN}==================================${NC}"
}

# 检查并创建服务文件
check_and_create_service_files() {
    local need_create=0
    local backend_service="/etc/systemd/system/handwriting-backend.service"
    local inference_service="/etc/systemd/system/handwriting-inference.service"

    # 检查服务文件是否存在
    if [ ! -f "$backend_service" ] || [ ! -f "$inference_service" ]; then
        need_create=1
        echo -e "${YELLOW}警告：检测到服务文件缺失${NC}"
        [ ! -f "$backend_service" ] && echo -e "${RED}  - $backend_service 不存在${NC}"
        [ ! -f "$inference_service" ] && echo -e "${RED}  - $inference_service 不存在${NC}"
    fi

    if [ $need_create -eq 1 ]; then
        echo ""
        read -p "是否创建缺失的 service 文件？(y/n): " create_confirm
        if [ "$create_confirm" = "y" ] || [ "$create_confirm" = "Y" ]; then
            # 如果需要创建，询问 venv 配置
            if [ -z "$BACKEND_VENV_PATH" ] && [ -z "$INFERENCE_VENV_PATH" ]; then
                configure_venv
            fi
            create_backend_service "$backend_service"
            create_inference_service "$inference_service"
            systemctl daemon-reload
            echo -e "${GREEN}Service 文件创建完成！${NC}"
        else
            echo -e "${YELLOW}跳过创建 service 文件${NC}"
            return 1
        fi
    fi
    return 0
}

# 创建后端服务文件
create_backend_service() {
    local service_file="$1"
    echo -e "${YELLOW}创建后端服务文件...${NC}"

    # 创建 PaddleX 缓存目录（解决权限问题）
    mkdir -p /var/www/.paddlex 2>/dev/null
    chown -R www-data:www-data /var/www/.paddlex 2>/dev/null
    chmod 755 /var/www/.paddlex 2>/dev/null

    # 创建并授权后端 logs 目录
    mkdir -p /opt/handwriting_recognition_system/backend/logs 2>/dev/null
    chown -R www-data:www-data /opt/handwriting_recognition_system/backend/logs 2>/dev/null
    chmod 755 /opt/handwriting_recognition_system/backend/logs 2>/dev/null

    # 创建并授权项目根目录 logs（用于 monitoring 日志）
    mkdir -p /opt/handwriting_recognition_system/logs 2>/dev/null
    chown -R www-data:www-data /opt/handwriting_recognition_system/logs 2>/dev/null
    chmod 755 /opt/handwriting_recognition_system/logs 2>/dev/null

    # 确定 Python 路径
    local python_path="python3"
    local path_env=""
    if [ "$USE_VENV" = true ] && [ -n "$BACKEND_VENV_PATH" ]; then
        python_path="$BACKEND_VENV_PATH/bin/uvicorn"
        path_env="PATH=$BACKEND_VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
    fi

    # 生成 Environment 行
    local env_lines=""
    env_lines+="Environment=\"LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib/gcc/x86_64-linux-gnu/13\"\n"

    if [ -n "$path_env" ]; then
        env_lines+="Environment=\"$path_env\"\n"
    fi

    env_lines+="EnvironmentFile=/opt/handwriting_recognition_system/.env\n"

    # 生成 ExecStart 行
    local exec_start_line=""
    if [ "$USE_VENV" = true ] && [ -n "$BACKEND_VENV_PATH" ]; then
        exec_start_line="ExecStart=$BACKEND_VENV_PATH/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
    else
        exec_start_line="ExecStart=/opt/handwriting_recognition_system/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
    fi

    cat > "$service_file" << EOF
[Unit]
Description=Handwriting Recognition Backend Service
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/handwriting_recognition_system/backend
Environment="TMPDIR=/tmp"
$env_lines
$exec_start_line
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=handwriting-backend

# Security settings (relaxed for Nix environment compatibility)
NoNewPrivileges=true
PrivateTmp=false
ProtectSystem=false
ProtectHome=false
ReadWritePaths=/opt/handwriting_recognition_system/uploads /opt/handwriting_recognition_system/models /tmp

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}✓ 后端服务文件已创建${NC}"
    if [ "$USE_VENV" = true ]; then
        echo -e "${GREEN}  使用 venv: $BACKEND_VENV_PATH${NC}"
    fi
}

# 创建推理服务文件
create_inference_service() {
    local service_file="$1"
    echo -e "${YELLOW}创建推理服务文件...${NC}"

    # 创建 PaddleX 缓存目录（解决权限问题）
    mkdir -p /var/www/.paddlex 2>/dev/null
    chown -R www-data:www-data /var/www/.paddlex 2>/dev/null
    chmod 755 /var/www/.paddlex 2>/dev/null

    # 生成 Environment 行
    local env_lines=""
    env_lines+="Environment=\"LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu\"\n"

    if [ "$USE_VENV" = true ] && [ -n "$INFERENCE_VENV_PATH" ]; then
        env_lines+="Environment=\"PATH=$INFERENCE_VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin\"\n"
    else
        env_lines+="Environment=\"PATH=/opt/handwriting_recognition_system/inference_service/venv/bin:/usr/local/bin:/usr/bin:/bin\"\n"
    fi

    env_lines+="EnvironmentFile=/opt/handwriting_recognition_system/.env\n"

    # 生成 ExecStart 行
    local exec_start_line=""
    if [ "$USE_VENV" = true ] && [ -n "$INFERENCE_VENV_PATH" ]; then
        exec_start_line="ExecStart=$INFERENCE_VENV_PATH/bin/python grpc_server/server.py"
    else
        exec_start_line="ExecStart=/opt/handwriting_recognition_system/inference_service/venv/bin/python grpc_server/server.py"
    fi

    cat > "$service_file" << EOF
[Unit]
Description=Handwriting Recognition Inference Service (gRPC)
After=network.target
After=handwriting-backend.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/handwriting_recognition_system/inference_service
Environment="TMPDIR=/tmp"
Environment="MPLCONFIGDIR=/tmp"
$env_lines
$exec_start_line
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=handwriting-inference

# Security settings (relaxed for Nix environment compatibility)
NoNewPrivileges=true
PrivateTmp=false
ProtectSystem=false
ProtectHome=false
ReadWritePaths=/opt/handwriting_recognition_system/uploads /opt/handwriting_recognition_system/models /tmp

# Optional: If GPU is available, uncomment the following lines
# DeviceAllow=/dev/nvidia0 rw
# DeviceAllow=/dev/nvidiactl rw
# DeviceAllow=/dev/nvidia-uvm rw

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}✓ 推理服务文件已创建${NC}"
    if [ "$USE_VENV" = true ]; then
        echo -e "${GREEN}  使用 venv: $INFERENCE_VENV_PATH${NC}"
    fi
}

# 启动所有服务
start_services() {
    # 检查并创建服务文件
    if ! check_and_create_service_files; then
        return 1
    fi

    echo -e "${YELLOW}启动字迹识别系统服务...${NC}"
    systemctl start handwriting-backend.service
    systemctl start handwriting-inference.service
    echo -e "${GREEN}所有服务已启动${NC}"
}

# 停止所有服务
stop_services() {
    echo -e "${YELLOW}停止字迹识别系统服务...${NC}"
    systemctl stop handwriting-inference.service
    systemctl stop handwriting-backend.service
    echo -e "${GREEN}所有服务已停止${NC}"
}

# 重启所有服务
restart_services() {
    echo -e "${YELLOW}重启字迹识别系统服务...${NC}"
    systemctl restart handwriting-backend.service
    systemctl restart handwriting-inference.service
    echo -e "${GREEN}所有服务已重启${NC}"
}

# 查看服务状态
show_status() {
    echo -e "${GREEN}=================================="
    echo "  后端服务状态"
    echo -e "==================================${NC}"
    systemctl status handwriting-backend.service --no-pager
    echo ""
    echo -e "${GREEN}=================================="
    echo "  推理服务状态"
    echo -e "==================================${NC}"
    systemctl status handwriting-inference.service --no-pager
}

# 查看后端日志
show_backend_logs() {
    echo -e "${GREEN}显示后端服务日志（Ctrl+C 退出）...${NC}"
    journalctl -u handwriting-backend.service -f
}

# 查看推理服务日志
show_inference_logs() {
    echo -e "${GREEN}显示推理服务日志（Ctrl+C 退出）...${NC}"
    journalctl -u handwriting-inference.service -f
}

# 重新加载配置
reload_services() {
    echo -e "${YELLOW}重新加载服务配置...${NC}"
    systemctl reload handwriting-backend.service
    echo -e "${GREEN}配置已重新加载${NC}"
}

# 启用开机自启
enable_autostart() {
    echo -e "${YELLOW}启用开机自启...${NC}"
    systemctl enable handwriting-backend.service
    systemctl enable handwriting-inference.service
    echo -e "${GREEN}已启用开机自启${NC}"
}

# 禁用开机自启
disable_autostart() {
    echo -e "${YELLOW}禁用开机自启...${NC}"
    systemctl disable handwriting-backend.service
    systemctl disable handwriting-inference.service
    echo -e "${GREEN}已禁用开机自启${NC}"
}

# 重新创建 service 文件
recreate_service_files() {
    echo -e "${YELLOW}重新创建 service 文件...${NC}"

    local backend_service="/etc/systemd/system/handwriting-backend.service"
    local inference_service="/etc/systemd/system/handwriting-inference.service"

    # 确认操作
    echo -e "${RED}注意：这将覆盖现有的 service 文件${NC}"
    read -p "是否继续？(y/n): " confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}已取消操作${NC}"
        return 1
    fi

    # 停止服务（如果正在运行）
    echo -e "${YELLOW}停止现有服务...${NC}"
    systemctl stop handwriting-backend.service 2>/dev/null
    systemctl stop handwriting-inference.service 2>/dev/null

    # 询问是否重新配置 venv
    echo ""
    read -p "是否重新配置 venv 路径？(y/n): " reconfig_venv
    if [ "$reconfig_venv" = "y" ] || [ "$reconfig_venv" = "Y" ]; then
        configure_venv
    fi

    # 创建服务文件
    create_backend_service "$backend_service"
    create_inference_service "$inference_service"

    # 重载 systemd
    systemctl daemon-reload

    echo -e "${GREEN}Service 文件重新创建完成！${NC}"
    echo -e "${YELLOW}提示：请使用选项1启动服务${NC}"
}

# 主循环
while true; do
    show_menu
    read -p "请输入选项: " choice
    case $choice in
        1) start_services ;;
        2) stop_services ;;
        3) restart_services ;;
        4) show_status ;;
        5) show_backend_logs ;;
        6) show_inference_logs ;;
        7) reload_services ;;
        8) enable_autostart ;;
        9) disable_autostart ;;
        10) recreate_service_files ;;
        11) configure_venv ;;
        0) echo "退出"; exit 0 ;;
        *) echo -e "${RED}无效选项${NC}" ;;
    esac
    echo ""
    read -p "按Enter键继续..."
done
