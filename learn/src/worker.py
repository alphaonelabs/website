"""
Education Platform – Cloudflare Python Worker
=============================================
Routes
  POST /api/init        – initialise DB schema
  POST /api/seed        – seed sample data
  POST /api/register    – register a new user
  POST /api/login       – authenticate, return signed token
  GET  /api/courses     – list courses (?category=&q=)
  POST /api/courses     – create course  [teacher]
  GET  /api/courses/:id – course + lessons (content gated behind enrolment)
  POST /api/enroll      – enrol in a course [student]
  GET  /api/dashboard   – personal dashboard
  POST /api/lessons     – create lesson  [teacher]
  POST /api/progress    – update lesson progress [student]

Security model
  • Course descriptions and lesson content are stored XOR-stream-cipher-encrypted
    at rest.  The key is SHA-256 derived from the ENCRYPTION_KEY env variable.
    ⚠️  XOR stream cipher is used here for demonstration; for production replace
    encrypt()/decrypt() with AES-GCM calls via `js.crypto.subtle`.
  • Passwords are stored as PBKDF2-SHA256 hashes with a unique per-user salt
    derived from the username and a global pepper.
  • Auth tokens are HMAC-SHA256 signed (stateless "JWT-lite").

Static HTML pages (public/) are served via the Workers KV site binding.
"""

import base64
import hashlib
import hmac as _hmac
import json
import re
from urllib.parse import urlparse, parse_qs

from workers import Response

# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from an arbitrary secret using SHA-256."""
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt(plaintext: str, secret: str) -> str:
    """
    Encrypt *plaintext* with a XOR stream-cipher (SHA-256 key expansion).

    The key is expanded into a keystream the same length as the data and
    each byte is XOR'd.  The result is Base64-encoded so it is safe to
    store as TEXT in D1.

    ⚠️  XOR stream cipher – demonstration only.
    For a production deployment replace this with AES-GCM via the
    Web Crypto API (available through `js.crypto.subtle`).
    """
    if not plaintext:
        return ""
    key = _derive_key(secret)
    data = plaintext.encode("utf-8")
    ks = (key * (len(data) // len(key) + 1))[: len(data)]
    return base64.b64encode(bytes(a ^ b for a, b in zip(data, ks))).decode("ascii")


def decrypt(ciphertext: str, secret: str) -> str:
    """Reverse of encrypt().  XOR is self-inverse so the algorithm is identical."""
    if not ciphertext:
        return ""
    try:
        key = _derive_key(secret)
        raw = base64.b64decode(ciphertext)
        ks = (key * (len(raw) // len(key) + 1))[: len(raw)]
        return bytes(a ^ b for a, b in zip(raw, ks)).decode("utf-8")
    except Exception:
        return "[decryption error]"


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# Global pepper mixed into every per-user salt to frustrate offline attacks
# even if the DB is leaked without the application secrets.
_PEPPER = b"edu-platform-cf-pepper-2024"
_PBKDF2_ITERS = 100_000


def _user_salt(username: str) -> bytes:
    """Derive a unique per-user salt from username + global pepper."""
    return hashlib.sha256(_PEPPER + username.encode("utf-8")).digest()


def hash_password(password: str, username: str) -> str:
    """Hash password with PBKDF2-SHA256 and a per-user derived salt."""
    salt = _user_salt(username)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERS)
    return base64.b64encode(dk).decode("ascii")


def verify_password(password: str, stored_hash: str, username: str) -> bool:
    return hash_password(password, username) == stored_hash


# ---------------------------------------------------------------------------
# HMAC-signed tokens (stateless "JWT-lite")
# ---------------------------------------------------------------------------

def create_token(user_id: int, username: str, role: str, secret: str) -> str:
    payload = base64.b64encode(
        json.dumps({"id": user_id, "username": username, "role": role}).encode()
    ).decode("ascii")
    sig = _hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_token(raw: str, secret: str):
    """Return the decoded payload dict or *None* if invalid."""
    if not raw:
        return None
    try:
        token = raw.removeprefix("Bearer ").strip()
        dot = token.rfind(".")
        if dot == -1:
            return None
        payload_b64, sig = token[:dot], token[dot + 1 :]
        expected = _hmac.new(
            secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return None
        # Re-pad base64 if needed
        padding = (4 - len(payload_b64) % 4) % 4
        return json.loads(base64.b64decode(payload_b64 + "=" * padding).decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def json_resp(data, status: int = 200):
    return Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json", **_CORS},
    )


def ok(data=None, msg: str = "OK"):
    body = {"success": True, "message": msg}
    if data is not None:
        body["data"] = data
    return json_resp(body, 200)


def err(msg: str, status: int = 400):
    return json_resp({"error": msg}, status)


# ---------------------------------------------------------------------------
# DB initialisation
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email    TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role     TEXT NOT NULL DEFAULT 'student',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title        TEXT NOT NULL,
        description  TEXT NOT NULL,
        teacher_id   INTEGER NOT NULL,
        category     TEXT NOT NULL DEFAULT 'General',
        difficulty   TEXT NOT NULL DEFAULT 'Beginner',
        enrolled_count INTEGER NOT NULL DEFAULT 0,
        created_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS enrollments (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id  INTEGER NOT NULL,
        progress   INTEGER NOT NULL DEFAULT 0,
        enrolled_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(student_id, course_id)
    )""",
    """CREATE TABLE IF NOT EXISTS lessons (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id  INTEGER NOT NULL,
        title      TEXT NOT NULL,
        content    TEXT NOT NULL,
        order_num  INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_courses_teacher      ON courses(teacher_id)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_student  ON enrollments(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_course   ON enrollments(course_id)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_course       ON lessons(course_id)",
]


async def init_db(env):
    for sql in _DDL:
        await env.DB.prepare(sql).run()


# ---------------------------------------------------------------------------
# Sample-data seeding
# ---------------------------------------------------------------------------

async def seed_db(env, enc_key: str):
    # ---- users ---------------------------------------------------------------
    sample_users = [
        ("alice",   "alice@example.com",   "password123", "teacher"),
        ("bob",     "bob@example.com",     "password123", "teacher"),
        ("charlie", "charlie@example.com", "password123", "student"),
        ("diana",   "diana@example.com",   "password123", "student"),
    ]
    for uname, email, pw, role in sample_users:
        try:
            await env.DB.prepare(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)"
            ).bind(uname, email, hash_password(pw, uname), role).run()
        except Exception:
            pass  # already exists

    alice = await env.DB.prepare("SELECT id FROM users WHERE username='alice'").first()
    bob   = await env.DB.prepare("SELECT id FROM users WHERE username='bob'").first()
    if not alice or not bob:
        return

    aid, bid = alice["id"], bob["id"]

    # ---- courses -------------------------------------------------------------
    raw_courses = [
        (
            "Python for Beginners",
            "Learn Python programming from scratch. Master variables, loops, "
            "functions, and object-oriented design in this hands-on course.",
            aid, "Programming", "Beginner",
        ),
        (
            "Web Development Fundamentals",
            "Build modern, responsive websites with HTML5, CSS3, and JavaScript. "
            "Covers Flexbox, Grid, fetch API, and accessible design.",
            aid, "Web Development", "Beginner",
        ),
        (
            "Data Science with Python",
            "Explore data wrangling and visualisation with pandas and matplotlib, "
            "then build predictive models with scikit-learn.",
            bid, "Data Science", "Intermediate",
        ),
        (
            "Advanced JavaScript",
            "Master closures, the prototype chain, async/await, Promises, "
            "ES2024 features, and modern front-end architecture patterns.",
            bid, "Programming", "Advanced",
        ),
        (
            "Machine Learning Basics",
            "From linear regression to neural networks: understand the maths, "
            "implement algorithms in Python, and evaluate real-world models.",
            aid, "AI & ML", "Intermediate",
        ),
        (
            "Database Design & SQL",
            "Design normalised relational schemas, write complex SQL queries, "
            "use indexes for speed, and understand transactions.",
            bid, "Database", "Beginner",
        ),
    ]

    for title, desc, tid, cat, diff in raw_courses:
        try:
            await env.DB.prepare(
                "INSERT INTO courses (title, description, teacher_id, category, difficulty)"
                " VALUES (?,?,?,?,?)"
            ).bind(title, encrypt(desc, enc_key), tid, cat, diff).run()
        except Exception:
            pass

    # ---- lessons for "Python for Beginners" ----------------------------------
    py_row = await env.DB.prepare(
        "SELECT id FROM courses WHERE title='Python for Beginners' LIMIT 1"
    ).first()
    if py_row:
        cid = py_row["id"]
        raw_lessons = [
            (
                "Introduction to Python",
                "# Welcome to Python\n\nPython is a high-level, dynamically typed language "
                "celebrated for its clean syntax.\n\n## Why Python?\n"
                "- Beginner-friendly\n- Huge ecosystem (PyPI has 500k+ packages)\n"
                "- Powers web, data, AI, automation\n\n## Your First Program\n"
                "```python\nprint('Hello, World!')\n```\n\n"
                "Run it in your terminal and you'll see: **Hello, World!**",
                1,
            ),
            (
                "Variables & Data Types",
                "# Variables and Data Types\n\nVariables are named containers for data.\n\n"
                "## Core Types\n| Type | Example |\n|------|---------|\n"
                "| int | `age = 25` |\n| float | `pi = 3.14` |\n"
                "| str | `name = 'Alice'` |\n| bool | `active = True` |\n\n"
                "```python\nname = 'Alice'\nage = 25\nprint(f'{name} is {age} years old')\n```",
                2,
            ),
            (
                "Control Flow",
                "# Control Flow\n\nGuide your program with conditions and loops.\n\n"
                "## if / elif / else\n```python\nscore = 85\n"
                "if score >= 90:\n    grade = 'A'\nelif score >= 80:\n    grade = 'B'\n"
                "else:\n    grade = 'C'\nprint(grade)  # B\n```\n\n"
                "## for Loop\n```python\nfor i in range(1, 6):\n    print(i)\n```\n\n"
                "## while Loop\n```python\ncount = 0\nwhile count < 3:\n    count += 1\n```",
                3,
            ),
            (
                "Functions",
                "# Functions\n\nFunctions let you reuse code and keep things organised.\n\n"
                "```python\ndef greet(name: str, loud: bool = False) -> str:\n"
                "    msg = f'Hello, {name}!'\n    return msg.upper() if loud else msg\n\n"
                "print(greet('Alice'))        # Hello, Alice!\n"
                "print(greet('Bob', loud=True))  # HELLO, BOB!\n```\n\n"
                "**Best practices**\n- One responsibility per function\n"
                "- Use type hints\n- Write docstrings",
                4,
            ),
        ]
        for title, content, order in raw_lessons:
            try:
                await env.DB.prepare(
                    "INSERT INTO lessons (course_id, title, content, order_num) VALUES (?,?,?,?)"
                ).bind(cid, title, encrypt(content, enc_key), order).run()
            except Exception:
                pass

        # enrol charlie in Python course
        charlie = await env.DB.prepare(
            "SELECT id FROM users WHERE username='charlie'"
        ).first()
        if charlie:
            try:
                await env.DB.prepare(
                    "INSERT OR IGNORE INTO enrollments (student_id, course_id, progress)"
                    " VALUES (?,?,?)"
                ).bind(charlie["id"], cid, 50).run()
                await env.DB.prepare(
                    "UPDATE courses SET enrolled_count=1 WHERE id=?"
                ).bind(cid).run()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# API handlers
# ---------------------------------------------------------------------------

async def api_register(req, env):
    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    username = (body.get("username") or "").strip()
    email    = (body.get("email")    or "").strip()
    password = (body.get("password") or "")
    role     = body.get("role", "student")

    if not username or not email or not password:
        return err("username, email, and password are required")
    if len(password) < 6:
        return err("Password must be at least 6 characters")
    if role not in ("student", "teacher"):
        role = "student"

    try:
        await env.DB.prepare(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)"
        ).bind(username, email, hash_password(password, username), role).run()
    except Exception as e:
        if "UNIQUE" in str(e):
            return err("Username already exists", 409)
        return err(f"Registration failed: {e}", 500)

    row = await env.DB.prepare(
        "SELECT id, username, role FROM users WHERE username=?"
    ).bind(username).first()

    token = create_token(row["id"], row["username"], row["role"], env.JWT_SECRET)
    return ok(
        {"token": token, "user": {"id": row["id"], "username": row["username"], "role": row["role"]}},
        "Registration successful",
    )


async def api_login(req, env):
    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    username = (body.get("username") or "").strip()
    password = (body.get("password") or "")

    if not username or not password:
        return err("username and password are required")

    row = await env.DB.prepare(
        "SELECT id, username, password_hash, role FROM users WHERE username=?"
    ).bind(username).first()

    if not row or not verify_password(password, row["password_hash"], row["username"]):
        return err("Invalid username or password", 401)

    token = create_token(row["id"], row["username"], row["role"], env.JWT_SECRET)
    return ok(
        {"token": token, "user": {"id": row["id"], "username": row["username"], "role": row["role"]}},
        "Login successful",
    )


async def api_list_courses(req, env):
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    category = (params.get("category") or [None])[0]
    search   = (params.get("q")        or [None])[0]

    if category:
        res = await env.DB.prepare(
            "SELECT c.id,c.title,c.description,c.category,c.difficulty,"
            "c.enrolled_count,c.created_at,u.username AS teacher_name"
            " FROM courses c JOIN users u ON c.teacher_id=u.id"
            " WHERE c.category=? ORDER BY c.created_at DESC"
        ).bind(category).all()
    else:
        res = await env.DB.prepare(
            "SELECT c.id,c.title,c.description,c.category,c.difficulty,"
            "c.enrolled_count,c.created_at,u.username AS teacher_name"
            " FROM courses c JOIN users u ON c.teacher_id=u.id"
            " ORDER BY c.created_at DESC"
        ).all()

    enc_key = env.ENCRYPTION_KEY
    courses = []
    for row in res.results or []:
        desc = decrypt(row["description"], enc_key)
        if search and search.lower() not in row["title"].lower() and search.lower() not in desc.lower():
            continue
        courses.append(
            {
                "id": row["id"],
                "title": row["title"],
                "description": desc,
                "category": row["category"],
                "difficulty": row["difficulty"],
                "enrolled_count": row["enrolled_count"],
                "teacher_name": row["teacher_name"],
                "created_at": row["created_at"],
            }
        )

    return json_resp({"courses": courses})


async def api_create_course(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user or user.get("role") != "teacher":
        return err("Teacher access required", 401)

    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    title      = (body.get("title")       or "").strip()
    description = (body.get("description") or "").strip()
    category   = (body.get("category")    or "General").strip()
    difficulty  = (body.get("difficulty")  or "Beginner").strip()

    if not title or not description:
        return err("title and description are required")

    try:
        await env.DB.prepare(
            "INSERT INTO courses (title,description,teacher_id,category,difficulty)"
            " VALUES (?,?,?,?,?)"
        ).bind(title, encrypt(description, env.ENCRYPTION_KEY), user["id"], category, difficulty).run()
    except Exception as e:
        return err(f"Failed to create course: {e}", 500)

    row = await env.DB.prepare(
        "SELECT c.*,u.username AS teacher_name FROM courses c"
        " JOIN users u ON c.teacher_id=u.id"
        " WHERE c.teacher_id=? ORDER BY c.id DESC LIMIT 1"
    ).bind(user["id"]).first()

    return ok({"id": row["id"], "title": row["title"]}, "Course created")


async def api_get_course(course_id: int, req, env):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)

    course = await env.DB.prepare(
        "SELECT c.*,u.username AS teacher_name"
        " FROM courses c JOIN users u ON c.teacher_id=u.id WHERE c.id=?"
    ).bind(course_id).first()

    if not course:
        return err("Course not found", 404)

    enc_key = env.ENCRYPTION_KEY

    is_enrolled = False
    enrollment = None
    if user:
        enrollment = await env.DB.prepare(
            "SELECT id,progress FROM enrollments WHERE student_id=? AND course_id=?"
        ).bind(user["id"], course_id).first()
        is_enrolled = enrollment is not None

    is_teacher = user and (
        user.get("role") == "teacher"
        and await env.DB.prepare(
            "SELECT id FROM courses WHERE id=? AND teacher_id=?"
        ).bind(course_id, user["id"]).first() is not None
    )

    lessons_res = await env.DB.prepare(
        "SELECT id,title,content,order_num FROM lessons"
        " WHERE course_id=? ORDER BY order_num"
    ).bind(course_id).all()

    lessons = []
    for row in lessons_res.results or []:
        entry = {"id": row["id"], "title": row["title"], "order_num": row["order_num"]}
        if is_enrolled or is_teacher:
            entry["content"] = decrypt(row["content"], enc_key)
        else:
            entry["content"] = None
        lessons.append(entry)

    return json_resp(
        {
            "course": {
                "id": course["id"],
                "title": course["title"],
                "description": decrypt(course["description"], enc_key),
                "category": course["category"],
                "difficulty": course["difficulty"],
                "enrolled_count": course["enrolled_count"],
                "teacher_name": course["teacher_name"],
                "created_at": course["created_at"],
            },
            "lessons": lessons,
            "is_enrolled": is_enrolled,
            "progress": enrollment["progress"] if enrollment else 0,
        }
    )


async def api_enroll(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    course_id = body.get("course_id")
    if not course_id:
        return err("course_id is required")

    course = await env.DB.prepare("SELECT id FROM courses WHERE id=?").bind(course_id).first()
    if not course:
        return err("Course not found", 404)

    try:
        await env.DB.prepare(
            "INSERT OR IGNORE INTO enrollments (student_id, course_id) VALUES (?,?)"
        ).bind(user["id"], course_id).run()
        await env.DB.prepare(
            "UPDATE courses SET enrolled_count="
            "(SELECT COUNT(*) FROM enrollments WHERE course_id=?) WHERE id=?"
        ).bind(course_id, course_id).run()
    except Exception as e:
        return err(f"Enrollment failed: {e}", 500)

    return ok(None, "Enrolled successfully")


async def api_dashboard(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    if user.get("role") == "teacher":
        res = await env.DB.prepare(
            "SELECT c.id,c.title,c.category,c.difficulty,c.enrolled_count,c.created_at,"
            "(SELECT COUNT(*) FROM lessons WHERE course_id=c.id) AS lesson_count"
            " FROM courses c WHERE c.teacher_id=? ORDER BY c.created_at DESC"
        ).bind(user["id"]).all()

        courses = [
            {
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "difficulty": r["difficulty"],
                "enrolled_count": r["enrolled_count"],
                "lesson_count": r["lesson_count"],
                "created_at": r["created_at"],
            }
            for r in (res.results or [])
        ]
        return json_resp({"user": user, "role": "teacher", "courses_taught": courses})

    else:
        res = await env.DB.prepare(
            "SELECT c.id,c.title,c.category,c.difficulty,e.progress,e.enrolled_at,"
            "u.username AS teacher_name"
            " FROM enrollments e"
            " JOIN courses c ON e.course_id=c.id"
            " JOIN users u ON c.teacher_id=u.id"
            " WHERE e.student_id=? ORDER BY e.enrolled_at DESC"
        ).bind(user["id"]).all()

        courses = [
            {
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "difficulty": r["difficulty"],
                "progress": r["progress"],
                "teacher_name": r["teacher_name"],
                "enrolled_at": r["enrolled_at"],
            }
            for r in (res.results or [])
        ]
        return json_resp({"user": user, "role": "student", "enrolled_courses": courses})


async def api_create_lesson(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user or user.get("role") != "teacher":
        return err("Teacher access required", 401)

    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    course_id = body.get("course_id")
    title     = (body.get("title")   or "").strip()
    content   = (body.get("content") or "").strip()
    order_num = int(body.get("order_num") or 0)

    if not course_id or not title or not content:
        return err("course_id, title, and content are required")

    owned = await env.DB.prepare(
        "SELECT id FROM courses WHERE id=? AND teacher_id=?"
    ).bind(course_id, user["id"]).first()
    if not owned:
        return err("Course not found or access denied", 404)

    try:
        await env.DB.prepare(
            "INSERT INTO lessons (course_id,title,content,order_num) VALUES (?,?,?,?)"
        ).bind(course_id, title, encrypt(content, env.ENCRYPTION_KEY), order_num).run()
    except Exception as e:
        return err(f"Failed to create lesson: {e}", 500)

    return ok(None, "Lesson created")


async def api_update_progress(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    try:
        body = await req.json()
    except Exception:
        return err("Invalid JSON body")

    course_id = body.get("course_id")
    progress  = int(body.get("progress") or 0)

    if not course_id:
        return err("course_id is required")

    progress = max(0, min(100, progress))
    try:
        await env.DB.prepare(
            "UPDATE enrollments SET progress=? WHERE student_id=? AND course_id=?"
        ).bind(progress, user["id"], course_id).run()
    except Exception as e:
        return err(f"Failed to update progress: {e}", 500)

    return ok(None, "Progress updated")


# ---------------------------------------------------------------------------
# Static-asset serving  (Workers Sites / __STATIC_CONTENT KV)
# ---------------------------------------------------------------------------

_MIME = {
    "html": "text/html; charset=utf-8",
    "css":  "text/css; charset=utf-8",
    "js":   "application/javascript; charset=utf-8",
    "json": "application/json",
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "svg":  "image/svg+xml",
    "ico":  "image/x-icon",
}


async def serve_static(path: str, env):
    if path in ("/", ""):
        key = "index.html"
    else:
        key = path.lstrip("/")
        # add .html extension to bare page names (e.g. /dashboard → dashboard.html)
        if "." not in key.split("/")[-1]:
            key += ".html"

    try:
        content = await env.__STATIC_CONTENT.get(key, "text")
    except Exception:
        content = None

    if content is None:
        # fallback: serve index for unknown routes
        try:
            content = await env.__STATIC_CONTENT.get("index.html", "text")
        except Exception:
            content = None

    if content is None:
        return Response("<h1>404 – Not Found</h1>", status=404, headers={"Content-Type": "text/html"})

    ext = key.rsplit(".", 1)[-1] if "." in key else "html"
    mime = _MIME.get(ext, "text/plain")
    return Response(content, headers={"Content-Type": mime, **_CORS})


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

async def on_fetch(request, env):
    path   = urlparse(request.url).path
    method = request.method.upper()

    # CORS pre-flight
    if method == "OPTIONS":
        return Response("", status=204, headers=_CORS)

    # --- API routes ---
    if path.startswith("/api/"):
        if path == "/api/init" and method == "POST":
            try:
                await init_db(env)
                return ok(None, "Database initialised")
            except Exception as e:
                return err(f"Init failed: {e}", 500)

        if path == "/api/seed" and method == "POST":
            try:
                await init_db(env)
                await seed_db(env, env.ENCRYPTION_KEY)
                return ok(None, "Sample data seeded")
            except Exception as e:
                return err(f"Seed failed: {e}", 500)

        if path == "/api/register" and method == "POST":
            return await api_register(request, env)

        if path == "/api/login" and method == "POST":
            return await api_login(request, env)

        if path == "/api/courses" and method == "GET":
            return await api_list_courses(request, env)

        if path == "/api/courses" and method == "POST":
            return await api_create_course(request, env)

        m = re.fullmatch(r"/api/courses/(\d+)", path)
        if m and method == "GET":
            return await api_get_course(int(m.group(1)), request, env)

        if path == "/api/enroll" and method == "POST":
            return await api_enroll(request, env)

        if path == "/api/dashboard" and method == "GET":
            return await api_dashboard(request, env)

        if path == "/api/lessons" and method == "POST":
            return await api_create_lesson(request, env)

        if path == "/api/progress" and method == "POST":
            return await api_update_progress(request, env)

        return err("API endpoint not found", 404)

    # --- Static files ---
    return await serve_static(path, env)
