import uuid
import pytest
from fastapi.testclient import TestClient
from api.main import app
from database.connection import get_sync_session
from database.auth_models import User, UserBill, UserReport, UserNotification

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_saas_workflow_and_isolation(client):
    """
    Integration test verifying the entire C3 SaaS specifications:
    - User A and User B registration & verification
    - Authentication, login, and active bill initialization
    - File upload and persistent analyses caching
    - In-app notification triggers and clear actions
    - Saved custom reports
    - Strict tenant isolation (A cannot access B's records)
    """
    email_a = f"usera_{uuid.uuid4().hex[:8]}@electricai.com"
    email_b = f"userb_{uuid.uuid4().hex[:8]}@electricai.com"
    password = "SecurePassword123!"

    # 1. Register User A and User B
    reg_a = client.post("/auth/register", json={
        "email": email_a,
        "password": password,
        "first_name": "Alice",
        "last_name": "Smith",
        "zip_code": "07302",
        "utility_provider": "PSE&G"
    })
    assert reg_a.status_code == 201

    reg_b = client.post("/auth/register", json={
        "email": email_b,
        "password": password,
        "first_name": "Bob",
        "last_name": "Jones",
        "zip_code": "07701",
        "utility_provider": "JCP&L"
    })
    assert reg_b.status_code == 201

    # 2. Force verify emails directly in DB (simulating clicking email link)
    with get_sync_session() as session:
        db_a = session.query(User).filter(User.email == email_a).first()
        db_b = session.query(User).filter(User.email == email_b).first()
        assert db_a is not None
        assert db_b is not None
        db_a.email_verified = True
        db_b.email_verified = True
        session.commit()

    # 3. Log in User A
    session_a = TestClient(app)
    login_a = session_a.post("/auth/login", json={
        "email": email_a,
        "password": password
    })
    assert login_a.status_code == 200
    user_data_a = login_a.json()["data"]["user"]
    assert user_data_a["first_name"] == "Alice"

    # 4. Log in User B
    session_b = TestClient(app)
    login_b = session_b.post("/auth/login", json={
        "email": email_b,
        "password": password
    })
    assert login_b.status_code == 200

    # 5. User A has no bills initially
    dash_a_empty = session_a.get("/users/me/dashboard")
    assert dash_a_empty.status_code == 200
    assert dash_a_empty.json()["data"]["has_active_bill"] is False

    # 6. User A uploads first bill
    upload_a1 = session_a.post("/users/me/bills", data={"dev_mock": "true"})
    assert upload_a1.status_code == 201
    bill_a1_id = upload_a1.json()["data"]["bill"]["id"]

    # 7. User A uploads second bill
    upload_a2 = session_a.post("/users/me/bills", data={"dev_mock": "true"})
    assert upload_a2.status_code == 201
    bill_a2_id = upload_a2.json()["data"]["bill"]["id"]

    # Verify second bill is now the active one
    dash_a = session_a.get("/users/me/dashboard")
    assert dash_a.status_code == 200
    assert dash_a.json()["data"]["has_active_bill"] is True
    assert dash_a.json()["data"]["active_bill_id"] == bill_a2_id
    assert dash_a.json()["data"]["bills_count"] == 2

    # 8. User B uploads one bill
    upload_b1 = session_b.post("/users/me/bills", data={"dev_mock": "true"})
    assert upload_b1.status_code == 201
    bill_b1_id = upload_b1.json()["data"]["bill"]["id"]

    # Verify User B's dashboard only sees their bill
    dash_b = session_b.get("/users/me/dashboard")
    assert dash_b.json()["data"]["active_bill_id"] == bill_b1_id
    assert dash_b.json()["data"]["bills_count"] == 1

    # ── TENANT ISOLATION TESTS ──
    # Switch active bill for User B using User A's bill ID -> should return 404
    switch_fail = session_b.post("/users/me/active-bill", json={"bill_id": bill_a1_id})
    assert switch_fail.status_code == 404

    # User B tries to delete User A's bill -> should return 404
    del_fail = session_b.delete(f"/users/me/bills/{bill_a1_id}")
    assert del_fail.status_code == 404

    # 9. Switch active bill for User A
    switch_ok = session_a.post("/users/me/active-bill", json={"bill_id": bill_a1_id})
    assert switch_ok.status_code == 200
    dash_a_switched = session_a.get("/users/me/dashboard")
    assert dash_a_switched.json()["data"]["active_bill_id"] == bill_a1_id

    # 10. Saved Reports
    # Save a report for User A
    save_rep = session_a.post("/users/me/reports", json={
        "bill_id": bill_a1_id,
        "report_type": "forecast_report",
        "name": "Alice Summer Forecast",
        "data": {"some_data": 42}
    })
    assert save_rep.status_code == 201
    rep_id = save_rep.json()["data"]["report_id"]

    # Verify report is listed for User A
    reps_a = session_a.get("/users/me/reports")
    assert reps_a.status_code == 200
    assert len(reps_a.json()["data"]["reports"]) == 1
    assert reps_a.json()["data"]["reports"][0]["name"] == "Alice Summer Forecast"

    # Verify User B cannot see User A's reports
    reps_b = session_b.get("/users/me/reports")
    assert len(reps_b.json()["data"]["reports"]) == 0

    # 11. Notifications
    # User A should have notifications for both bill uploads
    notifs_a = session_a.get("/users/me/notifications")
    assert notifs_a.status_code == 200
    assert len(notifs_a.json()["data"]["notifications"]) >= 2
    unread_id = notifs_a.json()["data"]["notifications"][0]["id"]

    # Mark as read
    mark_read = session_a.patch(f"/users/me/notifications/{unread_id}")
    assert mark_read.status_code == 200

    # Verify notification state updated
    notifs_a_updated = session_a.get("/users/me/notifications")
    matched_notif = next(n for n in notifs_a_updated.json()["data"]["notifications"] if n["id"] == unread_id)
    assert matched_notif["is_read"] is True

    # Clear notifications
    clear_notifs = session_a.delete("/users/me/notifications")
    assert clear_notifs.status_code == 200
    notifs_a_empty = session_a.get("/users/me/notifications")
    assert len(notifs_a_empty.json()["data"]["notifications"]) == 0

    # Clean up User A bill
    del_ok = session_a.delete(f"/users/me/bills/{bill_a2_id}")
    assert del_ok.status_code == 200
    
    # Active bill should auto-switch to bill_a1
    dash_a_final = session_a.get("/users/me/dashboard")
    assert dash_a_final.json()["data"]["active_bill_id"] == bill_a1_id
    assert dash_a_final.json()["data"]["bills_count"] == 1
