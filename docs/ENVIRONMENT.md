# 本地环境说明

> ⚠️ **首次接入本项目时，请先阅读并验证本文档**。
> 执行终端命令前，务必确认当前 shell 环境（WSL / PowerShell / CMD），选择正确的命令格式。

---

## 1. Shell 环境

**当前 Shell: WSL (Ubuntu on Windows)**

WSL 是 Linux 环境，Windows 路径规则不适用：

| 操作 | ❌ 错误写法 | ✅ 正确写法 |
|---|---|---|
| 切换到项目目录 | `cd D:\a_code\...` | `cd /mnt/d/a_code/A_Agents/Calibre_Agent/calibremcp` |
| 访问 Windows 文件 | `D:\path\to\file` | `/mnt/d/path/to/file` |
| 使用 Python 处理路径 | `os.chdir('D:\\path')` | `os.chdir('/mnt/d/path')` 或 `os.chdir('D:/path')` |

> 注意：WSL 中路径大小写敏感。`/mnt/d/A_Code/` 和 `/mnt/d/a_code/` 是不同的路径。

**通用方案 — 用 Python 处理 Windows 路径（WSL 和 PowerShell 都兼容）：**
```bash
# 在 WSL bash 中，要切换到 Windows 路径：用 Python 做中介
cd "$(python -c "import os; os.chdir('D:\a_code\A_Agents\Calibre_Agent\calibremcp'); print(os.getcwd())")"

# 或者直接让 Python 执行命令，不走 Shell cd
python -c "
import os, subprocess
os.chdir('D:\\a_code\\A_Agents\\Calibre_Agent\\calibremcp')
subprocess.run(['ls', '-la'])
"
```

---

## 2. 工具使用建议

**在 CherryStudio 中，优先使用专用工具而非 Bash 命令：**

| 你想做什么 | ✅ 用这个 | ❌ 不要用 Bash |
|---|---|---|
| 查找文件 | `Glob` 工具 | `find` 或 `ls` |
| 搜索代码 | `Grep` 工具 | `grep` 或 `rg` |
| 读取文件 | `Read` 工具 | `cat` 或 `head` |
| 修改文件 | `Edit` 工具 | `sed` 或 `awk` |
| 写入文件 | `Write` 工具 | `echo >` 或 `cat <<EOF` |

> 专用工具比 Bash 命令更高效、更准确，且不需要处理路径转换问题。

---

## 3. Python 环境管理

**项目使用 `uv` 管理虚拟环境和依赖，不使用 pip。**

| 操作 | ✅ 正确命令 | ❌ 不要用 |
|---|---|---|
| 安装依赖 | `uv sync` | `pip install -r requirements.txt` |
| 运行 Python | `uv run python -m calibre_mcp` | `python -m calibre_mcp` |
| 运行测试 | `uv run python -m pytest -v` | `pytest` |
| 代码检查 | `uv run ruff check .` | `ruff check .`（如果未全局安装） |
| 安装包 | `uv pip install <package>` | `pip install <package>` |
| 添加依赖 | `uv add <package>` | — |

> `uv sync` 会自动创建虚拟环境（在项目目录下的 `.venv/`），无需手动 `uv venv`。
> 首次检出项目后第一件事：`cd /mnt/d/.../calibremcp && uv sync`

---

## 4. MCP 配置（CherryStudio）

- **客户端**: CherryStudio（非 Claude Desktop）
- **命令**: `uv`
- **参数**: `--directory D:\a_code\A_Agents\Calibre_Agent\calibremcp run python -m calibre_mcp`
- **环境变量**: `CALIBRE_LIBRARY_PATH = E:\A_Books\Calibre书库\轻小说`

**启动方式对比：**

| 方式 | 命令 |
|---|---|
| CherryStudio 集成 | 通过 UI 配置，使用 uv 命令（见上） |
| 手动调试 | `uv --directory D:\a_code\A_Agents\Calibre_Agent\calibremcp run python -m calibre_mcp` |
| 本地运行（WSL） | `cd /mnt/d/a_code/A_Agents/Calibre_Agent/calibremcp && uv run python -m calibre_mcp` |

---

## 5. 书库信息

- **路径**: `E:\A_Books\Calibre书库\轻小说`
- **WSL 路径**: `/mnt/e/A_Books/Calibre书库/轻小说`
- **数据库文件**: 该目录下的 `metadata.db`
- **内容类型**: 轻小说
- **环境变量中的路径格式**: `E:\A_Books\Calibre书库\轻小说`（Windows 原生路径，CherryStudio 会将其传递给 uv）

---

## 6. 常见陷阱

### 陷阱 1: WSL `cd` 不支持 Windows 盘符
```bash
# ❌ WSL 中会报错
cd D:\a_code\A_Agents\Calibre_Agent\calibremcp
# bash: cd: D:\a_code\...: No such file or directory

# ✅ 正确写法
cd /mnt/d/a_code/A_Agents/Calibre_Agent/calibremcp
```

### 陷阱 2: Bash 中字符串引号嵌套问题
```bash
# ❌ 复杂 f-string 在 WSL bash 中导致语法错误
python -c "print(f"hello {name}")"  # 引号冲突

# ✅ 用单引号括整个 Python 脚本
python -c 'print("hello world")'

# ✅ 或者用 Python heredoc（推荐）
python << 'PYEOF'
name = "world"
print(f"hello {name}")
PYEOF
```

### 陷阱 3: 未使用 uv 直接调 Python
```bash
# ❌ 虚拟环境未激活时找不到依赖
python -m calibre_mcp

# ✅ 使用 uv 自动管理环境
uv run python -m calibre_mcp
```

### 陷阱 4: WSL 路径大小写敏感
```bash
# ❌ WSL 中 /mnt/d/A_Code/ 和 /mnt/d/a_code/ 是不同的路径
cd /mnt/d/A_Code/A_Agents/Calibre_Agent

# ✅ 路径必须与实际文件系统大小写一致
cd /mnt/d/a_code/A_Agents/Calibre_Agent/calibremcp
```

### 陷阱 5: Bash 管道命令在 WSL 下的特殊行为
```bash
# ❌ Windows 路径中的反斜杠会被 Bash 解释为转义符
ls D:\a_code\*  # \a 被解释为 BEL 字符

# ✅ 使用正斜杠
ls /mnt/d/a_code/
```

---

## 7. 验证环境是否正常

每次新 agent 首次接入时，建议按顺序执行以下检查：

```bash
# 1. 确认项目目录存在且正确
ls -la /mnt/d/a_code/A_Agents/Calibre_Agent/calibremcp/pyproject.toml

# 2. 确认 uv 可用
which uv && uv --version

# 3. 确认依赖已同步（首次务必执行）
uv sync

# 4. 确认书库路径有效
uv run python -c "
import sqlite3
conn = sqlite3.connect(r'E:\A_Books\Calibre书库\轻小说\metadata.db')
count = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
print(f'DB OK: {count} books')
"
```

---

## 8. 更新记录

- 2026-05-04: 初始创建，记录 WSL 环境、uv 管理、CherryStudio MCP 配置、常见陷阱
- 2026-05-04: 迭代：修复 cd() 示例 bug，新增工具使用建议（优先用 Glob/Grep/Read 而非 Bash），新增陷阱 5，验证命令改用 `uv run`
