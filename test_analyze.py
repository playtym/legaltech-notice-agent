import asyncio
from legaltech.app import analyze_case, AnalyzeRequest, Complainant
from fastapi import Request

async def main():
    payload = AnalyzeRequest(
        complainant=Complainant(full_name="Test", email="test@test.com", address="IN"),
        issue_summary="My flight was cancelled without prior notice. The airline has not provided the mandatory compensation as per DGCA regulations.",
        desired_resolution="Refund and compensation",
        company_name_hint="Airline",
        jurisdiction="India"
    )
    # mock request
    from fastapi import Request
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 80), "path": "/notice/analyze",
        "headers": []
    }
    request = Request(scope)
    try:
        res = await analyze_case(request, payload)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'src')
    asyncio.run(main())
