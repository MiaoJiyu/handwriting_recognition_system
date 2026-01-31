# 超级管理员命令行工具文档

## 概述

`scripts/super_admin.py` 提供了绕过前端限制的超级管理员操作功能。这些命令直接操作数据库，不受前端权限检查的限制。

## 使用方法

```bash
# 激活虚拟环境后
cd backend
source venv/bin/activate  # Linux/Mac
# 或
source venv/Scripts/activate  # Windows

# 运行命令
python scripts/super_admin.py <command> [args]
```

## 可用命令

### 1. delete - 强制删除用户

删除指定用户，**包括系统管理员**。

**语法：**
```bash
python scripts/super_admin.py delete <user_id> [--force]
```

**参数：**
- `user_id`：要删除的用户ID（必填）
- `--force`：跳过确认提示（可选）

**示例：**
```bash
# 删除系统管理员（需要确认）
python scripts/super_admin.py delete 1

# 强制删除（无需确认）
python scripts/super_admin.py delete 1 --force
```

**操作说明：**
- 显示目标用户信息（ID、用户名、昵称、角色、学校）
- 默认情况下会提示确认删除
- 使用 `--force` 参数可以跳过确认
- 删除成功后显示成功信息
- 如果用户不存在，显示错误信息

### 2. change_password - 强制修改用户密码

修改指定用户的密码，**包括系统管理员**。

**语法：**
```bash
python scripts/super_admin.py change_password <user_id> <new_password> [--force]
```

**参数：**
- `user_id`：用户ID（必填）
- `new_password`：新密码（必填）
- `--force`：跳过确认提示（可选）

**示例：**
```bash
# 修改系统管理员密码（需要确认）
python scripts/super_admin.py change_password 1 "newadminpassword123"

# 强制修改（无需确认）
python scripts/super_admin.py change_password 1 "newadminpassword123" --force
```

**操作说明：**
- 显示目标用户信息（ID、用户名、角色）
- 默认情况下会提示确认修改
- 使用 `--force` 参数可以跳过确认
- 密码长度验证：最少6位
- 修改成功后显示成功信息

### 3. update_role - 强制修改用户角色

修改指定用户的角色。

**语法：**
```bash
python scripts/super_admin.py update_role <user_id> <new_role> [--force]
```

**参数：**
- `user_id`：用户ID（必填）
- `new_role`：新角色（必填）
  - `student` - 学生
  - `teacher` - 教师
  - `school_admin` - 学校管理员
  - `system_admin` - 系统管理员
- `--force`：跳过确认提示（可选）

**示例：**
```bash
# 将用户降级为学生
python scripts/super_admin.py update_role 5 student

# 将用户提升为学校管理员（需要确认）
python scripts/super_admin.py update_role 5 school_admin

# 将用户提升为系统管理员（需要确认）
python scripts/super_admin.py update_role 5 system_admin

# 强制提升（无需确认）
python scripts/super_admin.py update_role 5 system_admin --force
```

**操作说明：**
- 显示目标用户信息（ID、用户名、当前角色、新角色）
- 默认情况下会提示确认修改
- 使用 `--force` 参数可以跳过确认
- 角色验证：只允许有效的角色值
- 修改成功后显示成功信息

### 4. delete_self - 删除当前登录用户

删除当前登录的用户（**仅用于测试目的**）。

**语法：**
```bash
python scripts/super_admin.py delete_self [--force]
```

**参数：**
- `--force`：跳过确认提示（可选）

**示例：**
```bash
# 删除自己（需要用户名和确认）
python scripts/super_admin.py delete_self
```

**操作说明：**
- 输入要删除的用户的用户名
- 默认情况下会显示危险警告并要求输入 'DELETE' 确认
- 使用 `--force` 参数可以跳过部分确认（但仍需用户名）
- 这是危险操作，仅用于测试目的

### 5. change_self_password - 修改当前用户密码

修改当前登录用户的密码（**仅用于测试目的**）。

**语法：**
```bash
python scripts/super_admin.py change_self_password [--force]
```

**参数：**
- `--force`：跳过确认提示（可选）

**示例：**
```bash
# 修改自己的密码
python scripts/super_admin.py change_self_password
```

**操作说明：**
- 输入要修改的用户的用户名
- 输入新密码
- 密码长度验证：最少6位
- 默认情况下会提示确认修改
- 使用 `--force` 参数可以跳过确认

### 6. list_users - 列出所有用户

列出系统中的所有用户。

**语法：**
```bash
python scripts/super_admin.py list_users
```

**示例：**
```bash
# 列出所有用户
python scripts/super_admin.py list_users
```

**输出示例：**
```
============================================================
用户列表（共 25 个用户）
============================================================

ID   | 用户名            | 昵称        | 角色              | 学校
-----+--------------------+--------------+-------------------+-------
1    | admin              | 超级管理员  | system_admin      | NULL
2    | school1_admin      | 管理员      | school_admin       | 1
3    | teacher1           | 王老师       | teacher           | 1
4    | student1           | 张三          | student           | 1
...
```

**操作说明：**
- 显示所有用户的完整列表
- 按 ID 升序排列
- 包含用户的全部信息

### 7. help - 显示帮助信息

显示所有可用命令的使用说明。

**语法：**
```bash
python scripts/super_admin.py help
```

## 安全说明

### ⚠️ 重要警告

1. **仅用于维护目的**
   - 这些命令绕过了前端的权限检查
   - 应该仅用于系统维护、紧急情况或测试
   - 不应该在日常操作中使用

2. **操作日志**
   - 每次操作都会输出详细的日志
   - 包括操作时间、目标用户、操作类型
   - 建议将命令行输出记录到日志文件

3. **确认机制**
   - 大多数危险操作都有确认提示
   - 使用 `--force` 参数可以跳过确认，但需谨慎使用

4. **密码安全**
   - 修改密码时，密码会以明文形式显示在命令行参数中
   - 建议避免在多用户系统中运行时被窥视
   - 操作完成后立即清除命令历史

5. **数据备份**
   - 在执行删除操作前，建议先备份数据库
   - 可以使用 `mysqldump` 或数据库管理工具备份

## 使用场景

### 场景 1：系统管理员忘记密码

```bash
# 查看系统管理员列表
python scripts/super_admin.py list_users

# 重置管理员密码
python scripts/super_admin.py change_password 1 "newsecurepassword123"
```

### 场景 2：紧急删除账户

```bash
# 快速删除问题账户（包括系统管理员）
python scripts/super_admin.py delete 999 --force
```

### 场景 3：权限调整

```bash
# 将用户提升为学校管理员
python scripts/super_admin.py update_role 123 school_admin

# 将学校管理员提升为系统管理员（需谨慎）
python scripts/super_admin.py update_role 123 system_admin
```

### 场景 4：批量操作脚本

可以创建 shell 脚本执行批量操作：

```bash
#!/bin/bash
# batch_operations.sh

# 批量修改密码
for id in 10 11 12 13 14; do
    python scripts/super_admin.py change_password $id "newpassword123" --force
done

# 批量调整角色
for id in 20 21 22; do
    python scripts/super_admin.py update_role $id teacher --force
done
```

## 与前端 API 的区别

| 操作 | 前端 API | 超级管理员命令 |
|------|-----------|----------------|
| 删除用户 | ❌ 不能删除系统管理员<br>❌ 不能删除自己 | ✅ 可以删除任何用户（包括系统管理员）|
| 修改密码 | ❌ 不能修改系统管理员密码 | ✅ 可以修改任何用户的密码（包括系统管理员）|
| 修改角色 | ❌ 不能设置为系统管理员 | ✅ 可以设置任何角色（包括系统管理员）|
| 权限检查 | 双重检查（前端+后端） | 无限制（直接数据库操作）|
| 操作确认 | 弹窗确认 | 命令行确认 |

## 故障排查

### 问题 1：无法连接数据库

**错误信息：**
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")
```

**解决方案：**
1. 检查 MySQL 服务是否运行
2. 检查 `.env` 文件中的数据库配置
3. 检查数据库用户名和密码

### 问题 2：权限错误

**错误信息：**
```
Permission denied: '/var/lib/mysql/...'
```

**解决方案：**
1. 使用有数据库权限的用户运行命令
2. 确保虚拟环境有必要的访问权限

### 问题 3：找不到用户

**错误信息：**
```
❌ 用户不存在：ID=999
```

**解决方案：**
1. 运行 `list_users` 命令查看所有用户
2. 确认用户 ID 正确

## 最佳实践

1. **操作前备份**
   ```bash
   # 备份数据库
   mysqldump -u root -p handwriting_recognition > backup_$(date +%Y%m%d).sql
   ```

2. **记录操作日志**
   ```bash
   # 将命令输出保存到日志文件
   python scripts/super_admin.py delete 1 2>&1 | tee -a admin_operations.log
   ```

3. **测试环境验证**
   - 先在测试环境验证操作
   - 确认没有问题后再在生产环境执行

4. **分阶段执行**
   - 对于复杂的批量操作，分阶段执行
   - 每阶段后验证结果

## 开发者说明

### 添加新命令

1. 在 `main()` 函数中添加新的命令分支
2. 实现相应的函数
3. 更新文档字符串和帮助信息
4. 添加适当的参数验证

### 数据库操作

所有数据库操作应该遵循以下模式：

```python
session = get_db_session()
try:
    # 执行数据库操作
    user = session.query(User).filter(User.id == user_id).first()
    # ... 操作逻辑 ...
    session.commit()
except Exception as e:
    session.rollback()
    # ... 错误处理 ...
finally:
    session.close()
```

## 注意事项

1. **命令历史安全**：在 Linux/Mac 系统上，命令会被保存到 `.bash_history` 或 `.zsh_history`
2. **进程监控**：使用 `ps aux | grep super_admin` 可以查看正在运行的命令
3. **审计日志**：建议启用数据库审计日志以跟踪敏感操作
4. **网络暴露**：此工具只能在服务器本地运行，不要通过 Web 界面暴露
