from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from utils.content_loader import get_faqs, get_guides, get_programs, get_stages

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.environ.get("SUPABASE_ANON_KEY", "").strip()
)
SUPABASE_COMMENTS_TABLE = os.environ.get("SUPABASE_COMMENTS_TABLE", "comments").strip() or "comments"
SUPABASE_TIMEOUT_SECONDS = 8

AVATAR_COLORS = {
    "sky": "bg-sky-500",
    "emerald": "bg-emerald-500",
    "amber": "bg-amber-500",
    "rose": "bg-rose-500",
    "violet": "bg-violet-500",
}


def get_current_user() -> dict[str, str]:
    name = session.get("user_name", "游客")
    avatar_seed = session.get("avatar_seed", "sky")
    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"

    return {
        "name": name,
        "avatar_seed": avatar_seed,
        "initial": (name[:1] if name else "游"),
    }


def get_completed_steps() -> set[str]:
    raw = session.get("completed_steps", [])
    if not isinstance(raw, list):
        return set()
    return {item for item in raw if isinstance(item, str)}


def save_completed_steps(step_keys: set[str]) -> None:
    session["completed_steps"] = sorted(step_keys)


def is_supabase_comments_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def build_supabase_headers(include_json: bool = False) -> dict[str, str]:
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE key is missing")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def list_comments_from_supabase(page_type: str, page_key: str) -> list[dict[str, object]]:
    if not is_supabase_comments_enabled():
        raise RuntimeError("Supabase comments is not configured")

    query = (
        "select=id,user_name,avatar_seed,content,created_at"
        f"&page_type=eq.{urllib.parse.quote(page_type, safe='')}"
        f"&page_key=eq.{urllib.parse.quote(page_key, safe='')}"
        "&order=id.desc"
    )
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_COMMENTS_TABLE}?{query}"
    request_obj = urllib.request.Request(url, headers=build_supabase_headers())

    try:
        with urllib.request.urlopen(request_obj, timeout=SUPABASE_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as err:
        raise RuntimeError("failed to fetch comments from Supabase") from err

    if not isinstance(data, list):
        raise RuntimeError("Supabase comments response is invalid")

    normalized: list[dict[str, object]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "id": row.get("id", 0),
                "user_name": row.get("user_name", "游客"),
                "avatar_seed": row.get("avatar_seed", "sky"),
                "content": row.get("content", ""),
                "created_at": row.get("created_at", ""),
            }
        )
    return normalized


def create_comment_in_supabase(
    page_type: str,
    page_key: str,
    user_name: str,
    avatar_seed: str,
    content: str,
    created_at: str,
) -> None:
    if not is_supabase_comments_enabled():
        raise RuntimeError("Supabase comments is not configured")

    payload = {
        "page_type": page_type,
        "page_key": page_key,
        "user_name": user_name,
        "avatar_seed": avatar_seed,
        "content": content,
        "created_at": created_at,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = build_supabase_headers(include_json=True)
    headers["Prefer"] = "return=minimal"

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_COMMENTS_TABLE}"
    request_obj = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request_obj, timeout=SUPABASE_TIMEOUT_SECONDS) as response:
            response.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as err:
        raise RuntimeError("failed to create comment in Supabase") from err


def list_comments(page_type: str, page_key: str) -> list[dict[str, object]]:
    if not is_supabase_comments_enabled():
        app.logger.warning("Supabase comments is not configured. Returning empty comments.")
        return []

    try:
        return list_comments_from_supabase(page_type, page_key)
    except RuntimeError as err:
        app.logger.warning("Supabase comments read failed: %s", err)
        return []


def create_comment(page_type: str, page_key: str, content: str) -> None:
    text = content.strip()
    if not text:
        raise ValueError("评论内容不能为空")
    if len(text) > 500:
        raise ValueError("评论不能超过 500 字")

    if not is_supabase_comments_enabled():
        raise ValueError("评论服务未配置 Supabase，请联系管理员设置环境变量。")

    user = get_current_user()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        create_comment_in_supabase(
            page_type,
            page_key,
            user["name"],
            user["avatar_seed"],
            text,
            created_at,
        )
    except RuntimeError as err:
        app.logger.error("Supabase comments write failed: %s", err)
        raise ValueError("评论服务暂时不可用，请稍后重试") from err


def find_faq_item(faq_id: int) -> dict[str, object] | None:
    for item in get_faqs():
        if item["id"] == faq_id:
            return item
    return None


def build_knowledge_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []

    for faq in get_faqs():
        chunks.append(
            {
                "source": f"常见问题 · {faq['question']}",
                "link": f"/faq/{faq['id']}",
                "content": str(faq["answer"]),
            }
        )

    for program in get_programs():
        summary = (
            f"{program['name']}，学院：{program['school']}，"
            f"方向：{program['focus']}，截止日期：{program['deadline']}，"
            f"语言要求：{program['language']}"
        )
        chunks.append(
            {
                "source": f"专业速查 · {program['name']}",
                "link": "/programs",
                "content": summary,
            }
        )

    for stage_slug, stage in get_guides().items():
        for step in stage["steps"]:
            content = " ".join(step["tutorial"]) + " " + " ".join(step["notes"])
            chunks.append(
                {
                    "source": f"操作步骤 · {stage['title']} / {step['title']}",
                    "link": f"/guide/{stage_slug}?step={step['id']}",
                    "content": content,
                }
            )

    return chunks


def ask_assistant(question: str) -> tuple[str, list[dict[str, str]]]:
    prompt = question.strip()
    if len(prompt) < 2:
        return "问题太短了，请补充更具体的需求，例如“推荐信要提前多久联系老师？”。", []

    chunks = build_knowledge_chunks()
    query = prompt.lower()
    tokens = [item for item in query.split() if item]
    query_chars = {char for char in query if not char.isspace()}

    scored: list[tuple[int, dict[str, str]]] = []
    for chunk in chunks:
        text = chunk["content"].lower()
        score = 0
        if query in text:
            score += 3
        for token in tokens:
            if token in text:
                score += 1
        score += len({char for char in query_chars if char in text})
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_chunks = [item for _, item in scored[:3]]

    if not top_chunks:
        default_answer = (
            "我暂时没有在现有资料里检索到直接答案。建议先去“常见问题”和“操作步骤”定位对应阶段，"
            "如果你愿意可以把问题写得更具体（例如专业名、截止时间、材料名称）。"
        )
        return default_answer, []

    lines = ["根据当前知识库，我建议你优先关注："]
    for index, chunk in enumerate(top_chunks, start=1):
        lines.append(f"{index}. {chunk['content']}")

    lines.append("以上内容来自项目内置资料，仅作申请准备参考，请最终以官网信息为准。")
    return "\n".join(lines), top_chunks


@app.context_processor
def inject_global_data() -> dict[str, object]:
    return {
        "current_user": get_current_user(),
        "stage_nav_items": get_stages(),
        "avatar_colors": AVATAR_COLORS,
    }


# ----------------------------
# 页面路由（GET）
# ----------------------------
@app.route("/")
def index() -> str:
    last_stage = request.cookies.get("last_stage", "")
    return render_template("index.html", stages=get_stages(), last_stage=last_stage)


@app.route("/programs")
def programs() -> str:
    return render_template("programs.html", programs=get_programs())


@app.route("/guide")
def guide_list() -> str:
    return render_template("guide_list.html", stages=get_stages())


@app.route("/guide/<stage_slug>")
def guide(stage_slug: str):
    guides = get_guides()
    stage = guides.get(stage_slug)
    if not stage:
        abort(404)

    steps = stage["steps"]
    requested_step_id = request.args.get("step", type=int)
    default_step_id = steps[0]["id"] if steps else None
    current_step_id = requested_step_id if requested_step_id is not None else default_step_id
    current_step = next((item for item in steps if item["id"] == current_step_id), None)

    if current_step is None:
        current_step = steps[0]

    page_key = f"{stage_slug}:{current_step['id']}"
    completed_steps = get_completed_steps()
    is_completed = page_key in completed_steps
    comments = list_comments("guide", page_key)

    response = make_response(
        render_template(
            "guide.html",
            stage_slug=stage_slug,
            stage=stage,
            current_step=current_step,
            comments=comments,
            page_key=page_key,
            is_completed=is_completed,
            completed_steps=completed_steps,
            completed_count=len(completed_steps),
        )
    )
    response.set_cookie("last_stage", stage_slug, max_age=60 * 60 * 24 * 14)
    return response


@app.route("/faq")
def faq_list() -> str:
    return render_template("faq.html", faqs=get_faqs())


@app.route("/faq/<int:faq_id>")
def faq_detail(faq_id: int) -> str:
    faq = find_faq_item(faq_id)
    if not faq:
        abort(404)

    comments = list_comments("faq", str(faq_id))
    return render_template("faq_detail.html", faq=faq, comments=comments)


@app.route("/assistant", methods=["GET", "POST"])
def assistant() -> str:
    question = ""
    answer = ""
    sources: list[dict[str, str]] = []

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer, sources = ask_assistant(question)

    return render_template(
        "assistant.html",
        question=question,
        answer=answer,
        sources=sources,
    )


# ----------------------------
# 交互路由（POST）
# ----------------------------
@app.route("/profile", methods=["POST"])
def update_profile():
    name = request.form.get("user_name", "").strip()
    avatar_seed = request.form.get("avatar_seed", "sky").strip()

    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"

    session["user_name"] = name[:20] if name else "游客"
    session["avatar_seed"] = avatar_seed

    flash("个人资料已更新", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/profile/reset", methods=["POST"])
def reset_profile():
    session.pop("user_name", None)
    session.pop("avatar_seed", None)
    session.pop("completed_steps", None)
    flash("已恢复默认身份并清空步骤状态", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/guide/<stage_slug>/comment", methods=["POST"])
def guide_comment(stage_slug: str):
    guides = get_guides()
    stage = guides.get(stage_slug)
    if not stage:
        abort(404)

    step_id = request.form.get("step_id", type=int, default=1)
    valid_step = next((step for step in stage["steps"] if step["id"] == step_id), None)
    if not valid_step:
        valid_step = stage["steps"][0]

    page_key = f"{stage_slug}:{valid_step['id']}"

    try:
        create_comment("guide", page_key, request.form.get("content", ""))
        flash("评论已发布", "success")
    except ValueError as err:
        flash(str(err), "error")

    return redirect(url_for("guide", stage_slug=stage_slug, step=valid_step["id"]))


@app.route("/guide/<stage_slug>/step/<int:step_id>/complete", methods=["POST"])
def toggle_step_complete(stage_slug: str, step_id: int):
    guides = get_guides()
    stage = guides.get(stage_slug)
    if not stage:
        abort(404)

    valid_step = next((step for step in stage["steps"] if step["id"] == step_id), None)
    if not valid_step:
        abort(404)

    step_key = f"{stage_slug}:{step_id}"
    completed_steps = get_completed_steps()

    if step_key in completed_steps:
        completed_steps.remove(step_key)
        completed = False
    else:
        completed_steps.add(step_key)
        completed = True

    save_completed_steps(completed_steps)

    return jsonify(
        {
            "ok": True,
            "step_key": step_key,
            "completed": completed,
            "completed_count": len(completed_steps),
        }
    )


@app.route("/faq/<int:faq_id>/comment", methods=["POST"])
def faq_comment(faq_id: int):
    faq = find_faq_item(faq_id)
    if not faq:
        abort(404)

    try:
        create_comment("faq", str(faq_id), request.form.get("content", ""))
        flash("评论已发布", "success")
    except ValueError as err:
        flash(str(err), "error")

    return redirect(url_for("faq_detail", faq_id=faq_id))


# ----------------------------
# 错误页
# ----------------------------
@app.errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
