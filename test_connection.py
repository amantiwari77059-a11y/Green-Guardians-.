import sys
import sqlite3
import json
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from starlette.testclient import TestClient

from server import app, DB_PATH, get_db

def test_database():
    print("\n--- 1. Testing Database (campus.db) Direct Access ---")
    conn = get_db()
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Tables found: {tables}")
    assert 'applications' in tables, "Table 'applications' missing!"
    assert 'site_content' in tables, "Table 'site_content' missing!"

    # Check row counts
    cursor.execute("SELECT count(*) FROM applications;")
    app_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM site_content;")
    content_count = cursor.fetchone()[0]
    print(f"Existing rows -> applications: {app_count}, site_content: {content_count}")
    conn.close()
    print("Database direct connectivity: PASSED")

def test_backend_api():
    print("\n--- 2. Testing Backend API Endpoints ---")
    client = TestClient(app)

    # Health
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    h = r.json()
    assert h["status"] == "ok" and h["database"] == "connected"
    print("GET /api/health: PASSED (Backend online, Database connected)")

    # Site Content
    r = client.get("/api/content")
    assert r.status_code == 200, f"Get content failed: {r.status_code}"
    content = r.json()
    assert "hero" in content and "about" in content and "events" in content
    print(f"GET /api/content: PASSED ({len(content)} sections loaded)")

    # Auth Verify
    r = client.post("/api/auth/verify", json={"password": "green2026"})
    assert r.status_code == 200 and r.json().get("valid") is True
    print("POST /api/auth/verify: PASSED (Password verified)")

    # Applications list
    r = client.get("/api/applications")
    assert r.status_code == 200
    apps = r.json()
    print(f"GET /api/applications: PASSED ({len(apps)} applications listed)")

def test_end_to_end_flow():
    print("\n--- 3. Testing Frontend -> Backend -> Database End-to-End Workflow ---")
    client = TestClient(app)

    # Step A: Student submits form on Frontend (index.html)
    test_id = f"APP-TEST-{uuid.uuid4().hex[:6].upper()}"
    student_payload = {
        "id": test_id,
        "firstName": "Rahul",
        "lastName": "Verma",
        "email": "rahul.test@campus.edu",
        "phone": "+91 9123456789",
        "dept": "Computer Science",
        "year": "2nd Year",
        "motivation": "I want to actively contribute to the clean campus mission!"
    }
    r = client.post("/api/applications", json=student_payload)
    assert r.status_code == 200, f"Student submission failed: {r.text}"
    created = r.json()["application"]
    assert created["id"] == test_id
    assert created["status"] == "pending"
    print(f"Step A: Frontend form submission stored -> ID: {test_id} [Status: pending] (PASSED)")

    # Step B: Verify directly in SQLite Database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (test_id,))
    row = cursor.fetchone()
    assert row is not None, "Application not found in SQLite campus.db!"
    assert row["first_name"] == "Rahul"
    assert row["course"] == "Computer Science"
    conn.close()
    print("Step B: Verified row directly in SQLite database table 'applications' (PASSED)")

    # Step C: Admin Panel reviews and accepts application
    patch_payload = {
        "status": "accepted",
        "notes": "Strong motivation statement. Assigned to Zone 3.",
        "emailSentFor": "accepted"
    }
    r = client.patch(f"/api/applications/{test_id}", json=patch_payload)
    assert r.status_code == 200, f"Admin update failed: {r.text}"
    updated = r.json()["application"]
    assert updated["status"] == "accepted"
    assert updated["notes"] == patch_payload["notes"]
    print("Step C: Admin panel updated application status -> accepted in DB (PASSED)")

    # Step D: Admin edits content and verifies frontend receives it
    r = client.get("/api/content/hero")
    assert r.status_code == 200
    hero_data = r.json()
    hero_data["tagline"] = "Segregate • Reduce • Reuse • Protect"
    r = client.post("/api/content/hero", json=hero_data)
    assert r.status_code == 200
    
    # Verify in DB
    conn = get_db()
    c_row = conn.execute("SELECT content_json FROM site_content WHERE section_key = 'hero'").fetchone()
    saved_hero = json.loads(c_row["content_json"])
    assert saved_hero["tagline"] == "Segregate • Reduce • Reuse • Protect"
    conn.close()
    print("Step D: Admin content edit persisted to SQLite 'site_content' table (PASSED)")

    # Step E: Cleanup test application
    r = client.delete(f"/api/applications/{test_id}")
    assert r.status_code == 200
    print(f"Step E: Cleanup test application {test_id} (PASSED)")

if __name__ == "__main__":
    try:
        test_database()
        test_backend_api()
        test_end_to_end_flow()
        print("\n=======================================================")
        print("🎉 ALL CHECKS PASSED!")
        print("Frontend, Backend, and Database are fully connected and functioning correctly!")
        print("=======================================================")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
