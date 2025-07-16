# FastAPI RESTful API 项目

本项目是一个基于 FastAPI 的 RESTful API，提供了一个健壮且可扩展的后端解决方案。它包含了用户认证、文章管理、请求限流和结构化日志等功能。

## 功能特性

*   **用户认证**：安全的用户注册、登录和令牌管理。
*   **文章管理**：文章的创建、读取、更新和删除（CRUD）操作。
*   **请求限流**：防止滥用并确保公平使用。
*   **结构化日志**：集中高效的日志记录，便于监控和调试。
*   **CORS 配置**：处理跨域资源共享。
*   **异常处理**：优雅地处理 HTTP 和一般异常。

## 项目结构

```
.
├── api/                  # API 路由和处理程序（用户、文章）
├── common/               # 常用工具、中间件、认证、日志
├── conf/                 # 配置文件
├── db/                   # 数据库相关文件（如果存在，main.py 中尚未完全实现）
├── logs/                 # 日志文件
├── models/               # 数据模型
├── service/              # 业务逻辑服务
├── main.py               # 应用程序主入口点
├── requirements.txt      # Python 依赖
└── README.md             # 项目 README
```

## 设置与安装

### 前提条件

*   Python 3.8+
*   pip

### 安装步骤

1.  **克隆仓库：**

    ```bash
    git clone https://github.com/your-username/fastapi-sonet.git
    cd fastapi-sonet
    ```

    （注意：如果可用，请将 `https://github.com/your-username/fastapi-sonet.git` 替换为实际的仓库 URL，或根据情况指导用户获取源代码。）

2.  **创建虚拟环境（推荐）：**

    ```bash
    python -m venv venv
    source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`
    ```

3.  **安装依赖：**

    ```bash
    pip install -r requirements.txt
    ```

## 运行应用

要启动 FastAPI 应用程序，请在项目根目录中运行以下命令：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

*   `main:app`：指代 `main.py` 文件中的 `app` 对象。
*   `--host 0.0.0.0`：使服务器可从任何 IP 地址访问。
*   `--port 8000`：在 8000 端口运行应用程序。
*   `--reload`：在代码更改时启用自动重新加载（对开发很有用）。
*   `--log-level info`：将日志级别设置为 info。

API 将在 `http://localhost:8000` 可用。

## API 文档

应用程序运行后，您可以通过以下地址访问交互式 API 文档 (Swagger UI)：

*   `http://localhost:8000/docs`

以及备用 API 文档 (ReDoc)：

*   `http://localhost:8000/redoc`

## 配置

本项目使用 `conf` 目录进行配置。您可以在 `conf/my_config.py` 中修改与项目名称、描述和其他参数相关的设置。

## 贡献

（可选：如果这是一个开源项目，请添加贡献指南）

## 许可证

（可选：添加许可证信息） 