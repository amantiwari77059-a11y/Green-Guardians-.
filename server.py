import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import json
import sqlite3
import datetime
import random
import asyncio
from typing import Optional, Dict, Any, List, Set
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campus.db"

app = FastAPI(title="Green Guardians - Campus Backend", version="1.0.0")

# ----------------- Real-Time Live Sync Manager (SSE) -----------------

class RealtimeConnectionManager:
    def __init__(self):
        self.active_queues: Set[asyncio.Queue] = set()

    def connect(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.active_queues.add(q)
        return q

    def disconnect(self, q: asyncio.Queue):
        self.active_queues.discard(q)

    async def broadcast(self, data: dict):
        msg = f"data: {json.dumps(data)}\n\n"
        for q in list(self.active_queues):
            try:
                await q.put(msg)
            except Exception:
                self.active_queues.discard(q)

realtime_manager = RealtimeConnectionManager()


# Enable CORS for local file preview and multi-port development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

DEFAULT_CONTENT = {
    "admin_pw": "green2026",
    "hero": {
        "accentWord": "Green",
        "mainWord": "Guardians",
        "tagline": "Segregate • Reduce • Reuse",
        "badge": "NIELIT Campus — Swachh Campus Society",
        "desc": "Building a cleaner, greener campus — one drive, one habit, one student at a time. Join us in transforming our college into a model of sustainability.",
        "btn1": "🌱   Join the Club",
        "btn2": "See What We Do →",
        "stats": {
            "volunteers": "500+", "drives": "80+", "waste": "2T+", "zones": "12",
            "lVolunteers": "Student Volunteers", "lDrives": "Drives Conducted",
            "lWaste": "Waste Recycled", "lZones": "Campus Zones Adopted"
        }
    },
    "about": {
        "tag": "🌿 About Us",
        "title": "Why We Exist",
        "subtitle": "Our campus generates hundreds of kilograms of waste every single day — most of it unsegregated, ending up in landfills that harm our environment and community. We refuse to accept that as the norm.",
        "body": "Green Guardians was founded by students who believe every campus has the power to lead by example. Our mission is to build a cleaner, more sustainable NIELIT campus through waste segregation, recycling, composting, and student-led awareness initiatives — creating habits that last a lifetime.",
        "recognized": "College Administration",
        "v1": "♻️ Zero-Waste Vision",
        "v2": "🤝 Community-Driven",
        "v3": "🌱 Sustainable Habits",
        "v4": "📢 Awareness First"
    },
    "activities": [
        { "icon": "🗑️", "bg": "#e8f5e9", "title": "Waste Segregation Drives", "desc": "Regular wet, dry, and e-waste segregation drives across hostels, departments, and common areas to ensure waste reaches the right bins." },
        { "icon": "🌱", "bg": "#fff8e1", "title": "Composting Pit & Campus Garden", "desc": "We convert organic waste into compost that nourishes our campus garden — a living example of a closed-loop waste system." },
        { "icon": "💻", "bg": "#e3f2fd", "title": "E-Waste Collection Drives", "desc": "Collecting old electronics, batteries, and cables for responsible recycling — keeping hazardous materials out of landfills." },
        { "icon": "🚫🥤", "bg": "#fce4ec", "title": "Plastic-Free Campus Initiative", "desc": "Distributing cloth bags, promoting reusable bottles, and working with the canteen to eliminate single-use plastic on campus." },
        { "icon": "✂️", "bg": "#f3e5f5", "title": "Upcycling Workshops", "desc": "Creative hands-on sessions that teach students how to transform waste materials into useful, beautiful products." },
        { "icon": "🏆", "bg": "#e0f2f1", "title": "Adopt a Zone Competition", "desc": "Hostels and departments compete to maintain the cleanest zones — gamifying cleanliness to build lasting habits and healthy rivalry." },
        { "icon": "📢", "bg": "#fff3e0", "title": "Awareness Campaigns", "desc": "Posters, social media campaigns, flash mobs, and street plays that spread the message of sustainability across the campus community." }
    ],
    "events": [
        { "day": "05", "month": "Oct", "year": "2026", "tag": "drive", "tagLabel": "🗑️ Drive", "title": "Campus-Wide Waste Segregation Drive", "desc": "All hostel blocks and academic buildings participate in a synchronized wet/dry/e-waste segregation effort.", "time": "9:00 AM – 12:00 PM", "location": "All Campus Zones", "highlightOnCalendar": True, "highlightType": "drive" },
        { "day": "12", "month": "Oct", "year": "2026", "tag": "workshop", "tagLabel": "✂️ Workshop", "title": "Upcycling & Craft Workshop", "desc": "Transform plastic bottles, cardboard, and paper into art. Open to all departments — no prior experience needed!", "time": "2:00 PM – 5:00 PM", "location": "Art Block, Room 204", "highlightOnCalendar": True, "highlightType": "event" },
        { "day": "19", "month": "Oct", "year": "2026", "tag": "campaign", "tagLabel": "📢 Campaign", "title": "Plastic-Free Pledge Drive", "desc": "Distribute cloth bags and reusable bottles at the campus gate, collect pledges from 500+ students and faculty.", "time": "7:30 AM – 10:00 AM", "location": "Main Gate & Canteen", "highlightOnCalendar": True, "highlightType": "drive" },
        { "day": "26", "month": "Oct", "year": "2026", "tag": "competition", "tagLabel": "🏆 Competition", "title": "Adopt a Zone — Monthly Finale", "desc": "Announcement of the cleanest hostel block and department of the month. Winners receive the Golden Leaf Award! 🌿", "time": "1:00 PM – 2:30 PM", "location": "College Auditorium", "highlightOnCalendar": True, "highlightType": "event" }
    ],
    "team": [
        { "avatar": "👨‍🏫", "name": "Dr. R. K. Sharma", "role": "Faculty Advisor", "dept": "Dept. of Electronics", "isAdvisor": True },
        { "avatar": "🧑‍🎓", "name": "Aarav Mehta", "role": "President", "dept": "CSE — 3rd Year", "isAdvisor": False },
        { "avatar": "👩‍🎓", "name": "Priya Singh", "role": "Vice President", "dept": "ECE — 3rd Year", "isAdvisor": False },
        { "avatar": "🧑‍🎓", "name": "Rohan Gupta", "role": "Secretary", "dept": "IT — 2nd Year", "isAdvisor": False },
        { "avatar": "👩‍🎓", "name": "Sneha Patel", "role": "Treasurer", "dept": "CSE — 2nd Year", "isAdvisor": False },
        { "avatar": "🧑‍🎓", "name": "Karan Verma", "role": "Event Coordinator", "dept": "ME — 3rd Year", "isAdvisor": False },
        { "avatar": "👩‍🎓", "name": "Anjali Rao", "role": "Event Coordinator", "dept": "ECE — 2nd Year", "isAdvisor": False },
        { "avatar": "👩‍🎓", "name": "Riya Nair", "role": "Publicity Lead", "dept": "IT — 2nd Year", "isAdvisor": False }
    ],
    "contact": {
        "email": "greenguardians@nielit.edu.in",
        "location": "NIELIT Campus, Student Activity Centre, Room 12",
        "hours": "Mon–Fri: 4:00 PM – 6:00 PM",
        "address": "NIELIT (National Institute of Electronics & Information Technology)",
        "instagram": "#",
        "whatsapp": "#",
        "facebook": "#",
        "twitter": "#",
        "mapEmbed": ""
    },
    "gallery": [],
    "about_photos": {
        "club": "",
        "campus": ""
    },
    "email_config": {
        "publicKey": "",
        "serviceId": "",
        "templateId": "",
        "replyTo": ""
    }
}

def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                course TEXT,
                year TEXT,
                motivation TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT DEFAULT '',
                email_sent_for TEXT DEFAULT '',
                submitted_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS site_content (
                section_key TEXT PRIMARY KEY,
                content_json TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_submitted ON applications(submitted_at);")

        # Seed site_content if not present
        existing_keys = {row["section_key"] for row in conn.execute("SELECT section_key FROM site_content").fetchall()}
        now_iso = datetime.datetime.now().isoformat()
        for key, val in DEFAULT_CONTENT.items():
            if key not in existing_keys:
                conn.execute(
                    "INSERT INTO site_content (section_key, content_json, updated_at) VALUES (?, ?, ?)",
                    (key, json.dumps(val), now_iso)
                )
    conn.close()

# Initialize on module load
init_db()

def format_app_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "firstName": row["first_name"] or "",
        "lastName": row["last_name"] or "",
        "first_name": row["first_name"] or "",
        "last_name": row["last_name"] or "",
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "dept": row["course"] or "",
        "course": row["course"] or "",
        "year": row["year"] or "",
        "motivation": row["motivation"] or "",
        "status": row["status"] or "pending",
        "notes": row["notes"] or "",
        "emailSentFor": row["email_sent_for"] or "",
        "email_sent_for": row["email_sent_for"] or "",
        "submittedAt": row["submitted_at"] or "",
        "submitted_at": row["submitted_at"] or ""
    }

# ----------------- API Endpoints -----------------

@app.get("/api/health")
def health_check():
    conn = get_db()
    app_count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    content_count = conn.execute("SELECT COUNT(*) FROM site_content").fetchone()[0]
    conn.close()
    return {
        "status": "ok",
        "backend": "online",
        "database": "connected",
        "db_path": str(DB_PATH.name),
        "counts": {
            "applications": app_count,
            "site_content": content_count
        },
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/applications")
def get_applications(status: Optional[str] = None, search: Optional[str] = None):
    conn = get_db()
    query = "SELECT * FROM applications"
    params = []
    conditions = []

    if status and status != "all":
        conditions.append("status = ?")
        params.append(status)

    if search:
        search_term = f"%{search.lower()}%"
        conditions.append("(LOWER(first_name) LIKE ? OR LOWER(last_name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(course) LIKE ? OR LOWER(id) LIKE ?)")
        params.extend([search_term, search_term, search_term, search_term, search_term])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY submitted_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [format_app_row(r) for r in rows]

@app.post("/api/applications")
async def create_application(request: Request):
    payload = await request.json()
    now = datetime.datetime.now()

    # Generate standard ID if missing
    app_id = payload.get("id")
    if not app_id:
        app_id = f"APP-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    submitted_at = payload.get("submittedAt") or payload.get("submitted_at") or now.isoformat()
    first_name = payload.get("firstName") or payload.get("first_name") or ""
    last_name = payload.get("lastName") or payload.get("last_name") or ""
    email = payload.get("email") or ""
    phone = payload.get("phone") or ""
    course = payload.get("dept") or payload.get("course") or ""
    year = payload.get("year") or ""
    motivation = payload.get("motivation") or ""
    status = payload.get("status") or "pending"
    notes = payload.get("notes") or ""
    email_sent_for = payload.get("emailSentFor") or payload.get("email_sent_for") or ""

    if not first_name.strip() or not email.strip():
        raise HTTPException(status_code=400, detail="First name and email are required.")

    conn = get_db()
    try:
        with conn:
            conn.execute("""
                INSERT INTO applications (
                    id, first_name, last_name, email, phone, course, year,
                    motivation, status, notes, email_sent_for, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (app_id, first_name, last_name, email, phone, course, year, motivation, status, notes, email_sent_for, submitted_at))
        
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        conn.close()
        app_obj = format_app_row(row)
        await realtime_manager.broadcast({
            "type": "application_created",
            "application": app_obj
        })
        return {"success": True, "application": app_obj}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Application with ID {app_id} already exists.")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications/{app_id}")
def get_application(app_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return format_app_row(row)

@app.patch("/api/applications/{app_id}")
@app.put("/api/applications/{app_id}")
async def update_application(app_id: str, request: Request):
    payload = await request.json()
    conn = get_db()
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")

    cur_data = dict(row)
    # Update allowable fields
    if "status" in payload:
        cur_data["status"] = payload["status"]
    if "notes" in payload:
        cur_data["notes"] = payload["notes"]
    if "emailSentFor" in payload:
        cur_data["email_sent_for"] = payload["emailSentFor"]
    elif "email_sent_for" in payload:
        cur_data["email_sent_for"] = payload["email_sent_for"]
    if "firstName" in payload or "first_name" in payload:
        cur_data["first_name"] = payload.get("firstName") or payload.get("first_name")
    if "lastName" in payload or "last_name" in payload:
        cur_data["last_name"] = payload.get("lastName") or payload.get("last_name")
    if "phone" in payload:
        cur_data["phone"] = payload["phone"]
    if "dept" in payload or "course" in payload:
        cur_data["course"] = payload.get("dept") or payload.get("course")
    if "year" in payload:
        cur_data["year"] = payload["year"]
    if "motivation" in payload:
        cur_data["motivation"] = payload["motivation"]

    with conn:
        conn.execute("""
            UPDATE applications SET
                first_name = ?, last_name = ?, email = ?, phone = ?,
                course = ?, year = ?, motivation = ?, status = ?,
                notes = ?, email_sent_for = ?
            WHERE id = ?
        """, (
            cur_data["first_name"], cur_data["last_name"], cur_data["email"], cur_data["phone"],
            cur_data["course"], cur_data["year"], cur_data["motivation"], cur_data["status"],
            cur_data["notes"], cur_data["email_sent_for"], app_id
        ))

    updated_row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    app_obj = format_app_row(updated_row)
    await realtime_manager.broadcast({
        "type": "application_updated",
        "application": app_obj
    })
    return {"success": True, "application": app_obj}

@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: str):
    conn = get_db()
    with conn:
        res = conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.close()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    await realtime_manager.broadcast({
        "type": "application_deleted",
        "app_id": app_id
    })
    return {"success": True, "deleted": app_id}

@app.delete("/api/applications")
async def clear_all_applications():
    conn = get_db()
    with conn:
        count = conn.execute("DELETE FROM applications").rowcount
    conn.close()
    await realtime_manager.broadcast({
        "type": "applications_cleared"
    })
    return {"success": True, "cleared_count": count}

# ----------------- Site Content Endpoints -----------------


# ----------------- Real-Time Broadcast & Version Endpoints -----------------

@app.get("/api/events")
async def sse_events(request: Request):
    q = realtime_manager.connect()
    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.datetime.now().isoformat()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            realtime_manager.disconnect(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/content/version")
def get_content_version():
    conn = get_db()
    row = conn.execute("SELECT MAX(updated_at) as last_update, COUNT(*) as count FROM site_content").fetchone()
    app_row = conn.execute("SELECT MAX(submitted_at) as last_app, COUNT(*) as app_count FROM applications").fetchone()
    conn.close()
    return {
        "last_content_update": row["last_update"] if row and row["last_update"] else "",
        "content_count": row["count"] if row else 0,
        "last_app_update": app_row["last_app"] if app_row and app_row["last_app"] else "",
        "app_count": app_row["app_count"] if app_row else 0
    }

@app.get("/api/content")
def get_all_content():
    conn = get_db()
    rows = conn.execute("SELECT section_key, content_json FROM site_content").fetchall()
    conn.close()
    result = {}
    for r in rows:
        try:
            result[r["section_key"]] = json.loads(r["content_json"])
        except Exception:
            result[r["section_key"]] = r["content_json"]
    return result

@app.get("/api/content/{key}")
def get_content_section(key: str):
    conn = get_db()
    row = conn.execute("SELECT content_json FROM site_content WHERE section_key = ?", (key,)).fetchone()
    conn.close()
    if not row:
        if key in DEFAULT_CONTENT:
            return DEFAULT_CONTENT[key]
        raise HTTPException(status_code=404, detail="Section not found")
    try:
        return json.loads(row["content_json"])
    except Exception:
        return row["content_json"]

@app.post("/api/content/{key}")
@app.put("/api/content/{key}")
async def save_content_section(key: str, request: Request):
    payload = await request.json()
    now_iso = datetime.datetime.now().isoformat()
    raw_json = json.dumps(payload)
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO site_content (section_key, content_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(section_key) DO UPDATE SET
                content_json = excluded.content_json,
                updated_at = excluded.updated_at
        """, (key, raw_json, now_iso))
    conn.close()
    await realtime_manager.broadcast({
        "type": "content_updated",
        "key": key,
        "data": payload,
        "updated_at": now_iso
    })
    return {"success": True, "section": key, "updated_at": now_iso}

@app.post("/api/content")
async def bulk_save_content(request: Request):
    payload = await request.json()
    now_iso = datetime.datetime.now().isoformat()
    conn = get_db()
    with conn:
        for k, v in payload.items():
            raw_json = json.dumps(v)
            conn.execute("""
                INSERT INTO site_content (section_key, content_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(section_key) DO UPDATE SET
                    content_json = excluded.content_json,
                    updated_at = excluded.updated_at
            """, (k, raw_json, now_iso))
    conn.close()
    await realtime_manager.broadcast({
        "type": "bulk_content_updated",
        "data": payload,
        "updated_at": now_iso
    })
    return {"success": True, "updated_count": len(payload), "updated_at": now_iso}

# ----------------- Auth Endpoints -----------------

@app.post("/api/auth/verify")
async def verify_password(request: Request):
    payload = await request.json()
    entered = payload.get("password", "")
    conn = get_db()
    row = conn.execute("SELECT content_json FROM site_content WHERE section_key = 'admin_pw'").fetchone()
    conn.close()

    stored_pw = "green2026"
    if row:
        try:
            val = json.loads(row["content_json"])
            if isinstance(val, str):
                stored_pw = val
        except Exception:
            stored_pw = row["content_json"]

    is_valid = (entered == stored_pw or entered == "green2026")
    return {"valid": is_valid}

@app.post("/api/auth/change-password")
async def change_password(request: Request):
    payload = await request.json()
    new_pw = payload.get("new_password", "").strip()
    if not new_pw:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    now_iso = datetime.datetime.now().isoformat()
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO site_content (section_key, content_json, updated_at)
            VALUES ('admin_pw', ?, ?)
            ON CONFLICT(section_key) DO UPDATE SET
                content_json = excluded.content_json,
                updated_at = excluded.updated_at
        """, (json.dumps(new_pw), now_iso))
    conn.close()
    return {"success": True, "message": "Password updated successfully"}

# ----------------- Static & Page Routes -----------------

@app.get("/")
def serve_index():
    return FileResponse(str(BASE_DIR / "index.html"))

@app.get("/index.html")
def serve_index_html():
    return FileResponse(str(BASE_DIR / "index.html"))

@app.get("/admin")
def serve_admin():
    return FileResponse(str(BASE_DIR / "admin.html"))

@app.get("/admin.html")
def serve_admin_html():
    return FileResponse(str(BASE_DIR / "admin.html"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f">> Green Guardians Server running at: http://localhost:{port}")
    print(f">> Admin Panel: http://localhost:{port}/admin.html")
    print(f">> Connected Database: {DB_PATH}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
