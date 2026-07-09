from database.connection import get_sync_session
from database.models import CustomerProfile, CustomerBill, CustomerUsageHistory, CustomerBillOCR

with get_sync_session() as session:
    profiles_cnt = session.query(CustomerProfile).count()
    bills_cnt = session.query(CustomerBill).count()
    hist_cnt = session.query(CustomerUsageHistory).count()
    ocr_cnt = session.query(CustomerBillOCR).count()
    
    print("Database counts:")
    print(f"  Customer Profiles: {profiles_cnt}")
    print(f"  Customer Bills: {bills_cnt}")
    print(f"  Usage History: {hist_cnt}")
    print(f"  OCR Runs: {ocr_cnt}")
