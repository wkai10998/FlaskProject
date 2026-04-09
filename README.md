# Flask 课程项目：港中文申请一站式助手

## 快速启动

```bash
cd /Users/wkai/Desktop/FlaskProject
pip install -r requirements.txt
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
- 登录页面：账号注册、登录、退出（Session）

## 技术知识点对应
- Flask 路由：`GET` 渲染页面、`POST` 提交交互
- Jinja2：`extends`、`include`、`block`、`for/if`
- Tailwind：响应式布局（`md:` / `lg:`）
- JavaScript：关键词筛选、步骤“标记完成”交互
- Session：登录状态、用户信息、步骤完成状态
- 数据层：
  - `content/*.json` 管理静态内容
  - Supabase `users` 存账号（邮箱 + 密码哈希）
  - Supabase `comments` 存评论（绑定 `user_id`）

## Supabase 配置（用户 + 评论）

1. 在 Supabase SQL Editor 执行 [supabase_comments.sql](/Users/wkai/Desktop/FlaskProject/docs/supabase_comments.sql)
2. 复制 [.env.example](/Users/wkai/Desktop/FlaskProject/.env.example) 为 `.env`（项目会自动读取）
3. 启动前设置：

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<your-service-role-key>"
```

可选变量：
- `SUPABASE_ANON_KEY`：未提供 `SUPABASE_SERVICE_ROLE_KEY` 时可用
- `SUPABASE_COMMENTS_TABLE`：默认 `comments`
- `SUPABASE_USERS_TABLE`：默认 `users`

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
│   │   ├── components/
│   │   │   └── login_modal.js
│   │   ├── programs.js
│   │   ├── faq.js
│   │   └── guide.js
│   └── images/guides/*.svg
├── templates/
│   ├── base.html
│   ├── header.html
│   ├── footer.html
│   ├── components/
│   │   ├── auth/
│   │   │   └── login_modal.html
│   │   └── home/
│   │       ├── hero_section.html
│   │       ├── timeline_section.html
│   │       └── cta_section.html
│   ├── index.html
│   ├── programs.html
│   ├── guide_list.html
│   ├── guide.html
│   ├── faq.html
│   ├── faq_detail.html
│   ├── assistant.html
│   ├── login.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── utils/
│   ├── __init__.py
│   ├── content_loader.py
│   └── supabase_client.py
└── tests/
    ├── test_auth_session.py
    ├── test_course_structure.py
    └── test_supabase_comments.py
```

## 汇报技术方案（Part2-Part7）

> 说明：本节只覆盖你要求的 Part2-Part7（不含 Part1、Part8、Part9）。

### Part2：项目结构与工作流（含产品演示、路由与 redirect）

#### 1) 项目结构（Flask + Jinja2 标准教学结构）
- 单入口：`app.py`（集中管理路由、业务逻辑、Session）
- 数据访问层：`utils/supabase_client.py`（统一处理 Supabase users/comments 读写）
- 模板：`templates/`（`base.html` 只负责 include 与 block；页面按 `components/` 组织）
- 静态资源：`static/css`、`static/js`
- 内容数据：`content/*.json`（阶段、步骤、专业、FAQ）
- 数据库：Supabase（用户与评论持久化）

#### 2) 请求工作流（前后端协作）
1. 浏览器访问页面（GET）  
2. Flask 路由读取 `content/*.json` 或 Supabase 数据  
3. Jinja2 渲染 HTML 返回前端  
4. 用户提交表单或点击交互（POST / JS fetch）  
5. 后端更新 Session 或写入 Supabase，再 `redirect` 回目标页面  

#### 3) 路由与 redirect 讲解点
- 页面路由（GET）：`/`、`/programs`、`/guide`、`/guide/<stage_slug>`、`/faq`、`/faq/<id>`、`/assistant`
- 交互路由（POST）：`/auth/login`、`/auth/register`、`/auth/logout`、`/profile`、`/guide/.../comment`、`/faq/.../comment`、`/guide/.../complete`
- redirect 典型场景：
  - 登录失败 -> 重定向回原页面并自动弹出登录框
  - 注册成功 -> 重定向到首页
  - 评论提交后 -> 重定向回原详情页（避免重复提交）

#### 4) 产品演示建议顺序（课堂汇报可直接用）
1. 首页路线图（讲信息架构）
2. 专业速查（讲前端筛选）
3. 操作步骤页（讲“标记已完成”与评论）
4. FAQ 页（讲搜索与评论）
5. 登录页（讲 Session 登录态）
6. 智能助手（讲 RAG 思路与来源）

### Part3：前端（Tailwind + 响应式）

#### 1) 核心页面
- 首页：时间路线图（按申请阶段组织）
- 专业速查：卡片列表 + 关键字段展示
- 操作步骤：左侧步骤导航 + 中间教程内容 + 右侧材料清单

#### 2) 响应式设计讲解点
- 使用 Tailwind 断点类：`md:`、`lg:`
- 典型布局：`grid grid-cols-1 lg:grid-cols-12`
- 移动端导航与桌面端导航分离显示（`hidden md:flex`）
- 保持移动端单列、桌面端多列，保证信息不拥挤

#### 3) 组件化页面组织（Jinja2）
- 统一骨架：`base.html`
- 公共组件：`header.html`、`footer.html`
- 页面模板通过 `{% extends %}` + `{% block %}` 复用结构
- 导航、登录态、用户信息通过模板上下文统一注入

### 模板分层规范（已落地）
- `base.html`：只保留全局骨架与 include，不写具体业务页面内容
- `templates/components/home/`：首页分段组件（hero/timeline/cta）
- `templates/components/auth/`：认证相关组件（如登录弹窗）
- 页面模板（如 `index.html`）只负责组合组件，不堆叠大段 HTML

### Part4：JavaScript 交互

#### 1) 评论发布与状态切换
- 评论发布：通过表单 POST 到 Flask（后端校验 + 入库）
- 步骤状态切换：`guide.js` 使用 `fetch` 调用 `/guide/.../complete`，返回 JSON 后局部更新按钮文案与计数

#### 2) 动态筛选/搜索/局部刷新
- `programs.js`：按专业名/学院/方向实时筛选卡片
- `faq.js`：按问题/答案/分类实时筛选
- 局部刷新：步骤完成状态只更新局部 DOM，不整页刷新

#### 3) 教学重点
- 事件监听（`input` / `click`）
- 异步请求（`fetch` + `async/await`）
- 基础错误提示（如 `window.alert`）

### Part5：后端与登录（Flask Session + Supabase）

#### 1) Flask 路由与表单
- GET 负责页面渲染，POST 负责数据写入和状态变更
- 表单提交后统一走后端校验（必填、长度、登录态）

#### 2) Session 登录态
- 登录成功后写入：`user_id`、`user_name`、`user_email`、`avatar_seed`
- 页面通过 `current_user.is_authenticated` 控制“登录按钮/用户菜单/评论权限”
- 退出登录时清理 Session 中的身份信息

#### 3) Supabase 持久化职责
- `users` 表：保存注册账号（邮箱 + 密码哈希 + 昵称）
- `comments` 表：保存评论数据，并通过 `user_id` 绑定用户
- 后端使用 `service_role key` 在服务端安全访问 Supabase（不暴露到前端）

### Part6：数据（BeautifulSoup）

#### 1) 数据流程（汇报建议画成流程图）
1. BeautifulSoup 抓取官网页面（招生要求/截止日期/材料说明）
2. 解析 HTML，提取字段（项目名、学院、DDL、语言要求等）
3. 清洗标准化（去噪、去重、格式统一）
4. 写入 Supabase 或导出为 JSON 供页面读取
5. 前端页面展示 + AI 检索共用同一份结构化数据

#### 2) 清洗规则建议（可讲专业性）
- 时间统一为同一格式（如 `YYYY-MM-DD`）
- 专业名称做同义词归一（避免检索漏召回）
- 保留 `source_url` 与 `updated_at` 字段，支持来源追溯和更新检查

### Part7：AI 助手（RAG）+ Error Handle

#### 1) RAG 方案（课堂可讲版本）
- 知识源：
  - 抓取后的官网内容（权威信息）
  - 你们整理的申请经验与FAQ（补充解释）
- 流程：
  1. 用户提问
  2. 检索最相关片段（关键词或向量检索）
  3. 将片段作为上下文交给模型生成回答
  4. 返回答案 + 来源链接（source）

#### 2) 如何减少幻觉
- 只允许基于检索到的上下文回答（无命中则明确“未检索到”）
- 设置回答模板：结论 + 依据 + 来源
- 对关键字段（日期、要求）优先引用结构化数据

#### 3) 来源追溯设计
- 每条知识保留 `source`、`link`、`updated_at`
- 回答中显示“来自哪个页面/哪条FAQ”
- 便于老师检查“答案是否可验证”

#### 4) Error Handle（异常处理）
- 前端：请求失败给出用户可理解提示（如“状态更新失败，请稍后重试”）
- 后端：参数校验失败返回友好提示并 `flash`
- 数据层：Supabase 网络错误、表结构缺失时返回明确错误文案
- 页面级：Flask 统一 `404/500` 错误页，避免白屏
