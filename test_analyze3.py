from fastapi.testclient import TestClient
from legaltech.app import app

client = TestClient(app)

response = client.post(
    "/notice/analyze",
    json={
        "complainant": {},
        "issue_summary": "My flight was cancelled completely without notice",
        "desired_resolution": "Refund completely",
        "company_name_hint": "Airline",
        "jurisdiction": "India"
    }
)
print("Status:", response.status_code)
print("Response:", response.text)
