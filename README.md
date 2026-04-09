# Flask 课程项目：港中文申请一站式助手

## 快速启动

```bash
cd /Users/wkai/Desktop/FlaskProject
.venv/bin/python app.py
```

访问：
- http://127.0.0.1:5000/
- http://127.0.0.1:5000/programs
- http://127.0.0.1:5000/guide
- http://127.0.0.1:5000/faq
- http://127.0.0.1:5000/assistant

## 页面结构（课程版）
- 首页：申请时间路线图
- 专业速查：项目信息筛选
- 操作步骤：阶段 -> 步骤 -> 评论
- 常见问题：FAQ 列表、详情、评论
- 智能助手：RAG 思路演示（检索 + 回答 + 来源）

## 技术知识点对应
- Flask 路由：`GET` 渲染页面、`POST` 提交交互
- Jinja2：`extends`、`include`、`block`、`for/if`
- Tailwind：响应式布局（`md:` / `lg:`）
- JavaScript：关键词筛选、步骤“标记完成”交互
- Session：昵称、头像色、步骤完成状态
- 数据层：
  - `content/*.json` 管理静态内容
  - 评论直接写入 Supabase（纯 Supabase 模式）

## Supabase 评论配置（第 3 步）

1. 在 Supabase SQL Editor 执行 [supabase_comments.sql](/Users/wkai/Desktop/FlaskProject/docs/supabase_comments.sql)
2. 复制 [.env.example](/Users/wkai/Desktop/FlaskProject/.env.example) 为 `.env`（或直接导出环境变量）
3. 启动前设置：

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<your-service-role-key>"
```

可选变量：
- `SUPABASE_ANON_KEY`：未提供 `SUPABASE_SERVICE_ROLE_KEY` 时可用
- `SUPABASE_COMMENTS_TABLE`：默认 `comments`

## 目录结构

```text
FlaskProject/
├── app.py
├── content/
│   ├── stages.json
│   ├── guide_steps.json
│   ├── programs.json
│   └── faq.json
├── docs/
│   ├── presentation_notes.md
│   ├── team_split.md
│   └── supabase_comments.sql
├── static/
│   ├── css/app.css
│   ├── js/
│   │   ├── programs.js
│   │   ├── faq.js
│   │   └── guide.js
│   └── images/guides/*.svg
├── templates/
│   ├── base.html
│   ├── header.html
│   ├── footer.html
│   ├── index.html
│   ├── programs.html
│   ├── guide_list.html
│   ├── guide.html
│   ├── faq.html
│   ├── faq_detail.html
│   ├── assistant.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── utils/
│   ├── __init__.py
│   └── content_loader.py
└── tests/
    ├── test_course_structure.py
    └── test_supabase_comments.py
```
