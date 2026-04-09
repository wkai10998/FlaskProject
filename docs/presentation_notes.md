# 展示讲解要点（简版）

## 一、项目主线
- 首页：申请路线图（按阶段进入操作步骤）
- 专业速查：项目信息检索与筛选
- 操作步骤：教程、材料清单、评论区、完成状态
- 常见问题：FAQ 列表 + 详情评论
- 智能助手：RAG 思路演示（检索 + 回答 + 来源）

## 二、技术点覆盖
- Flask 路由（`GET` 页面渲染、`POST` 交互提交）
- Jinja2（`extends/include/block` 模板结构）
- Tailwind 响应式布局（`md:` / `lg:`）
- JavaScript 交互（关键词筛选、步骤标记完成）
- Session（用户昵称、头像色、步骤完成状态）
- JSON 内容管理（`content/*.json`）
- Supabase 评论持久化（纯 Supabase 模式）
- 错误处理（404/500）

## 三、目录亮点
- `app.py`：集中管理路由，适合课堂讲解
- `templates/`：`base + header/footer + 页面模板`
- `static/js/`：按功能拆分脚本
- `content/`：结构化静态数据
- `utils/content_loader.py`：统一读取 JSON 数据
