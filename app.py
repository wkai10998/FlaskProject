from __future__ import annotations

import os
import urllib.parse
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
from werkzeug.security import check_password_hash

from utils.content_loader import get_faqs, get_guides, get_programs, get_stages
from utils.knowledge_base import build_knowledge_chunks
from utils.rag_pipeline import ask_with_rag
from utils import supabase_client

try:
    from dotenv import load_dotenv
except ImportError:  # optional dependency in development
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

AVATAR_COLORS = {
    "sky": "bg-sky-500",
    "emerald": "bg-emerald-500",
    "amber": "bg-amber-500",
    "rose": "bg-rose-500",
    "violet": "bg-violet-500",
}


def _clean_redirect_target(raw_url: str, default_endpoint: str = "index") -> str:
    target = raw_url.strip()
    if not target:
        return url_for(default_endpoint)

    parsed = urllib.parse.urlparse(target)
    if target.startswith("//"):
        return url_for(default_endpoint)
    if parsed.scheme or parsed.netloc:
        # Allow absolute referrer URLs from the same host only.
        if parsed.scheme in {"http", "https"} and parsed.netloc == request.host:
            parsed = urllib.parse.ParseResult(
                scheme="",
                netloc="",
                path=parsed.path or "/",
                params=parsed.params,
                query=parsed.query,
                fragment=parsed.fragment,
            )
        else:
            return url_for(default_endpoint)

    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_items = [
        (key, value) for key, value in query_items if key not in {"open_login", "auth_tab"}
    ]
    cleaned_query = urllib.parse.urlencode(query_items)

    return urllib.parse.urlunparse(
        ("", "", parsed.path or "/", parsed.params, cleaned_query, parsed.fragment)
    )


def _resolve_next_url(default_endpoint: str = "index") -> str:
    candidate = (
        request.form.get("next", "").strip()
        or request.args.get("next", "").strip()
        or (request.referrer or "").strip()
    )
    return _clean_redirect_target(candidate, default_endpoint=default_endpoint)


def _with_open_login_flag(target_url: str, auth_tab: str = "login") -> str:
    parsed = urllib.parse.urlparse(target_url)
    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_items = [
        (key, value) for key, value in query_items if key not in {"open_login", "auth_tab"}
    ]
    query_items.append(("open_login", "1"))
    query_items.append(("auth_tab", "register" if auth_tab == "register" else "login"))
    updated_query = urllib.parse.urlencode(query_items)

    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, updated_query, parsed.fragment)
    )


def get_current_user() -> dict[str, object]:
    user_id = session.get("user_id", "")
    email = session.get("user_email", "")
    name = session.get("user_name", "游客")
    avatar_seed = session.get("avatar_seed", "sky")
    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"

    return {
        "id": user_id,
        "email": email,
        "is_authenticated": bool(user_id),
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
    return supabase_client.is_supabase_enabled()


def list_comments_from_supabase(page_type: str, page_key: str) -> list[dict[str, object]]:
    return supabase_client.list_comments(page_type, page_key)


def create_comment_in_supabase(
    page_type: str,
    page_key: str,
    user_id: str,
    user_name: str,
    avatar_seed: str,
    content: str,
    created_at: str,
) -> None:
    supabase_client.create_comment(
        page_type=page_type,
        page_key=page_key,
        user_id=user_id,
        user_name=user_name,
        avatar_seed=avatar_seed,
        content=content,
        created_at=created_at,
    )


def get_user_by_email_from_supabase(email: str) -> dict[str, object] | None:
    return supabase_client.get_user_by_email(email)


def create_user_in_supabase(name: str, email: str, password: str, avatar_seed: str) -> dict[str, object]:
    return supabase_client.create_user(name, email, password, avatar_seed)


def update_user_profile_in_supabase(user_id: str, name: str, avatar_seed: str) -> dict[str, object]:
    return supabase_client.update_user_profile(user_id, name, avatar_seed)


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

    current_user = get_current_user()
    if not current_user["is_authenticated"]:
        raise ValueError("请先登录后发表评论")

    if not is_supabase_comments_enabled():
        raise ValueError("评论服务未配置 Supabase，请联系管理员设置环境变量。")

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        create_comment_in_supabase(
            page_type,
            page_key,
            str(current_user["id"]),
            str(current_user["name"]),
            str(current_user["avatar_seed"]),
            text,
            created_at,
        )
    except RuntimeError as err:
        app.logger.error("Supabase comments write failed: %s", err)
        raise ValueError(str(err)) from err


def find_faq_item(faq_id: int) -> dict[str, object] | None:
    for item in get_faqs():
        if item["id"] == faq_id:
            return item
    return None


def ask_assistant_local(question: str) -> tuple[str, list[dict[str, str]]]:
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


def ask_assistant_with_rag(question: str) -> tuple[str, list[dict[str, str]]]:
    return ask_with_rag(question)


def answer_assistant_question(question: str) -> tuple[str, list[dict[str, str]]]:
    prompt = question.strip()
    if len(prompt) < 2:
        return ask_assistant_local(prompt)

    try:
        return ask_assistant_with_rag(prompt)
    except RuntimeError as err:
        app.logger.warning("RAG failed, fallback to local retrieval: %s", err)
        return ask_assistant_local(prompt)


def ask_assistant(question: str) -> tuple[str, list[dict[str, str]]]:
    return answer_assistant_question(question)


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

    response = make_response(
        render_template(
            "guide.html",
            stage_slug=stage_slug,
            stage=stage,
            current_step=current_step,
            page_key=page_key,
            is_completed=is_completed,
            completed_steps=completed_steps,
            completed_count=len(completed_steps),
        )
    )
    response.set_cookie("last_stage", stage_slug, max_age=60 * 60 * 24 * 14)
    return response


@app.route("/guide/<stage_slug>/step/<int:step_id>/comments")
def guide_comments_api(stage_slug: str, step_id: int):
    guides = get_guides()
    stage = guides.get(stage_slug)
    if not stage:
        abort(404)

    valid_step = next((step for step in stage["steps"] if step["id"] == step_id), None)
    if valid_step is None:
        abort(404)

    page_key = f"{stage_slug}:{step_id}"
    comments = list_comments("guide", page_key)
    return jsonify({"comments": comments})


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


@app.route("/login")
def login_page() -> str:
    next_url = _resolve_next_url(default_endpoint="index")
    if next_url == url_for("login_page"):
        next_url = url_for("index")
    return redirect(_with_open_login_flag(next_url, auth_tab=request.args.get("auth_tab", "login")))


# ----------------------------
# 交互路由（POST）
# ----------------------------
@app.route("/auth/login", methods=["POST"])
def auth_login():
    next_url = _resolve_next_url(default_endpoint="index")
    if next_url == url_for("login_page"):
        next_url = url_for("index")

    if not is_supabase_comments_enabled():
        flash("登录服务未配置 Supabase，请联系管理员。", "error")
        return redirect(_with_open_login_flag(next_url))

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        flash("请输入邮箱和密码。", "error")
        return redirect(_with_open_login_flag(next_url))

    try:
        user = get_user_by_email_from_supabase(email)
    except RuntimeError as err:
        flash(str(err), "error")
        return redirect(_with_open_login_flag(next_url))

    if not user:
        flash("账号不存在，请先注册。", "error")
        return redirect(_with_open_login_flag(next_url))

    stored_hash = str(user.get("password_hash", ""))
    if not stored_hash or not check_password_hash(stored_hash, password):
        flash("邮箱或密码错误。", "error")
        return redirect(_with_open_login_flag(next_url))

    user_id = str(user.get("id", "")).strip()
    user_name = str(user.get("name", "用户")).strip()[:20] or "用户"
    avatar_seed = str(user.get("avatar_seed", "sky")).strip()
    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"

    session["user_id"] = user_id
    session["user_name"] = user_name
    session["user_email"] = email
    session["avatar_seed"] = avatar_seed

    flash("登录成功。", "success")
    return redirect(next_url)


@app.route("/auth/register", methods=["POST"])
def auth_register():
    next_url = _resolve_next_url(default_endpoint="index")
    if next_url == url_for("login_page"):
        next_url = url_for("index")

    if not is_supabase_comments_enabled():
        flash("注册服务未配置 Supabase，请联系管理员。", "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))

    name = request.form.get("name", "").strip()[:20]
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    avatar_seed = request.form.get("avatar_seed", "sky").strip()

    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"
    if not name:
        flash("请输入昵称。", "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))
    if "@" not in email or "." not in email:
        flash("请输入有效邮箱。", "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))
    if len(password) < 6:
        flash("密码至少 6 位。", "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))

    try:
        created_user = create_user_in_supabase(name, email, password, avatar_seed)
    except ValueError as err:
        flash(str(err), "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))
    except RuntimeError as err:
        flash(str(err), "error")
        return redirect(_with_open_login_flag(next_url, auth_tab="register"))

    session["user_id"] = str(created_user.get("id", "")).strip()
    session["user_name"] = str(created_user.get("name", name)).strip()[:20] or name
    session["user_email"] = str(created_user.get("email", email)).strip()
    session["avatar_seed"] = str(created_user.get("avatar_seed", avatar_seed)).strip()
    if session["avatar_seed"] not in AVATAR_COLORS:
        session["avatar_seed"] = "sky"

    flash("注册成功并已登录。", "success")
    return redirect(next_url)


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("user_name", None)
    session.pop("avatar_seed", None)
    flash("已退出登录。", "success")
    return redirect(url_for("index"))


@app.route("/profile", methods=["POST"])
def update_profile():
    current_user = get_current_user()
    if not current_user["is_authenticated"]:
        flash("请先登录后再修改资料。", "error")
        return redirect(_with_open_login_flag(_resolve_next_url(default_endpoint="index")))

    name = request.form.get("user_name", "").strip()[:20]
    avatar_seed = request.form.get("avatar_seed", "sky").strip()

    if avatar_seed not in AVATAR_COLORS:
        avatar_seed = "sky"
    if not name:
        name = str(current_user["name"]).strip()[:20] or "用户"

    try:
        updated_user = update_user_profile_in_supabase(str(current_user["id"]), name, avatar_seed)
    except RuntimeError as err:
        flash(str(err), "error")
        return redirect(request.referrer or url_for("index"))

    session["user_name"] = str(updated_user.get("name", name)).strip()[:20] or "用户"
    session["avatar_seed"] = str(updated_user.get("avatar_seed", avatar_seed)).strip()
    if session["avatar_seed"] not in AVATAR_COLORS:
        session["avatar_seed"] = "sky"

    flash("个人资料已更新", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/profile/reset", methods=["POST"])
def reset_profile():
    if not get_current_user()["is_authenticated"]:
        flash("请先登录后再修改资料。", "error")
        return redirect(_with_open_login_flag(_resolve_next_url(default_endpoint="index")))

    current_email = session.get("user_email", "")
    current_id = session.get("user_id", "")

    if current_id:
        try:
            update_user_profile_in_supabase(str(current_id), "用户", "sky")
        except RuntimeError as err:
            flash(str(err), "error")
            return redirect(request.referrer or url_for("index"))

    session.pop("user_name", None)
    session.pop("avatar_seed", None)
    session.pop("completed_steps", None)
    if current_id:
        session["user_id"] = current_id
    if current_email:
        session["user_email"] = current_email
    session["user_name"] = "用户"
    session["avatar_seed"] = "sky"
    flash("已恢复默认资料并清空步骤状态", "success")
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

    target_url = url_for("guide", stage_slug=stage_slug, step=valid_step["id"])

    try:
        create_comment("guide", page_key, request.form.get("content", ""))
        flash("评论已发布", "success")
    except ValueError as err:
        message = str(err)
        flash(message, "error")
        if "请先登录后发表评论" in message:
            target_url = _with_open_login_flag(target_url)

    return redirect(target_url)


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

    target_url = url_for("faq_detail", faq_id=faq_id)

    try:
        create_comment("faq", str(faq_id), request.form.get("content", ""))
        flash("评论已发布", "success")
    except ValueError as err:
        message = str(err)
        flash(message, "error")
        if "请先登录后发表评论" in message:
            target_url = _with_open_login_flag(target_url)

    return redirect(target_url)


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
    app.run(debug=True, port=5050)
