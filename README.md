# Flask 课程项目：港中文申请一站式助手

## 快速启动

```bash
cd /Users/wkai/Desktop/FlaskProject
pip install -r requirements.txt
.venv/bin/python app.py
```
访问：
- http://127.0.0.1:5050/
- http://127.0.0.1:5050/programs
- http://127.0.0.1:5050/guide
- http://127.0.0.1:5050/assistant

说明：
- 项目本地默认固定使用 `5050` 端口。

## 页面结构
- 首页：功能入口总览（Programs / Guides / Assistant）
- 专业速查：项目信息筛选
- 操作步骤：阶段 -> 步骤 -> 评论
- 智能助手：RAG 思路演示（检索 + 回答 + 来源）
- 登录弹窗：账号注册、登录、退出（Session）

## 数据同步
- BeautifulSoup 抓取流程已完成，但属于离线一次性抓取。
- 抓取后的数据需要先清洗，再写入本项目数据文件。
- 当前项目不做“官网更新后页面自动实时同步”。
- 抓取产出主要用于：
  - 更新 `content/programs.json`（专业速查）
  - 补充 RAG 使用的知识内容（如 `content/rag_kb.txt` 或其上游数据）

## Supabase 配置（用户 + 评论）

1. 在 Supabase SQL Editor 执行 [supabase_comments.sql](/Users/wkai/Desktop/FlaskProject/docs/supabase_comments.sql)
2. 在 Supabase SQL Editor 执行 [supabase_rag.sql](/Users/wkai/Desktop/FlaskProject/docs/supabase_rag.sql)
3. 复制 [.env.example](/Users/wkai/Desktop/FlaskProject/.env.example) 为 `.env`（项目会自动读取）
4. 启动前设置：

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<your-service-role-key>"
export ZHIPU_API_KEY="<your-zhipu-api-key>"
```

可选变量：
- `SUPABASE_ANON_KEY`：未提供 `SUPABASE_SERVICE_ROLE_KEY` 时可用
- `SUPABASE_COMMENTS_TABLE`：默认 `comments`
- `SUPABASE_USERS_TABLE`：默认 `users`
- `ZHIPU_CHAT_MODEL`：例如 `glm-4.7-flash`
- `ZHIPU_EMBEDDING_MODEL`：默认 `embedding-3`
- `ZHIPU_API_BASE`：默认 `https://open.bigmodel.cn/api/paas/v4`
- `RAG_EMBEDDING_DIM`：默认 `1024`（必须与 `supabase_rag.sql` 一致）

## RAG 初始化步骤（智能助手）

1. 把外部补充知识写入 `content/rag_kb.txt`  
2. 执行向量入库脚本（会自动切片 + 调 embedding + 写入 Supabase）：

```bash
.venv/bin/python scripts/ingest_rag.py
```

3. 启动 Flask：

```bash
.venv/bin/python app.py
```

4. 打开 [http://127.0.0.1:5050/assistant](http://127.0.0.1:5050/assistant) 测试  
5. 若智谱或向量检索异常，系统会自动回退到本地关键词检索，保证页面可用

## 目录结构

```text
FlaskProject/
├── app.py
├── content/
│   ├── stages.json
│   ├── guide_steps.json
│   ├── programs.json
│   └── rag_kb.txt
├── docs/
│   ├── presentation_notes.md
│   ├── team_split.md
│   ├── supabase_comments.sql
│   └── supabase_rag.sql
├── scripts/
│   └── ingest_rag.py
├── static/
│   ├── css/app.css
│   ├── js/
│   │   ├── components/
│   │   │   └── login_modal.js
│   │   ├── programs.js
│   │   └── guide.js
│   └── images/guides/*.svg
├── templates/
│   ├── base.html
│   ├── header.html
│   ├── footer.html
│   ├── login_modal.html
│   ├── index.html
│   ├── programs.html
│   ├── guide_list.html
│   ├── guide.html
│   ├── assistant.html
│   ├── disclaimer.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── utils/
│   ├── __init__.py
│   ├── content_loader.py
│   ├── knowledge_base.py
│   ├── supabase_client.py
│   ├── zhipu_client.py
│   └── rag_pipeline.py
└── tests/
    ├── test_assistant_rag.py
    ├── test_auth_session.py
    ├── test_course_structure.py
    ├── test_knowledge_base.py
    ├── test_rag_pipeline.py
    └── test_supabase_comments.py
```