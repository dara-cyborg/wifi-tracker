#!/usr/bin/env python3
"""
Phase 1 Sanity Check Test Script for Bakong KHQR Integration

This test script validates:
1. Bakong configuration loads correctly
2. QR code generation works with correct format
3. MD5 hash is properly generated
4. Payment status checking works against Bakong API
5. API response formats match expectations

Run this BEFORE Phase 2 to ensure data structures are correct.

Usage:
    python test_bakong_phase1.py

Prerequisites:
    - Environment variables set:
      - BAKONG_DEVELOPER_TOKEN
      - BAKONG_MERCHANT_ACCOUNT_ID
      - BAKONG_MERCHANT_NAME (optional)
      - BAKONG_MERCHANT_CITY (optional)
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging to see all output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_phase1():
    """Run Phase 1 sanity checks"""
    
    print("\n" + "="*80)
    print("BAKONG KHQR INTEGRATION - PHASE 1 SANITY CHECK")
    print("="*80 + "\n")
    
    # Step 1: Check environment variables
    print("[1/5] Checking environment variables...")
    try:
        token = os.getenv("BAKONG_DEVELOPER_TOKEN")
        account = os.getenv("BAKONG_MERCHANT_ACCOUNT_ID")
        
        if not token:
            print("  ❌ BAKONG_DEVELOPER_TOKEN not set")
            return False
        if not account:
            print("  ❌ BAKONG_MERCHANT_ACCOUNT_ID not set")
            return False
        
        print(f"  ✓ Token present: {token[:20]}...")
        print(f"  ✓ Merchant account: {account}")
    except Exception as e:
        print(f"  ❌ Error checking env vars: {e}")
        return False
    
    # Step 2: Import and test config loading
    print("\n[2/5] Loading Bakong configuration...")
    try:
        from backend.bakong import BakongConfig
        config = BakongConfig()
        print(f"  ✓ Config loaded successfully")
        print(f"    - Token: {config.token[:20]}...")
        print(f"    - Merchant: {config.merchant_account}")
        print(f"    - Name: {config.merchant_name}")
        print(f"    - City: {config.merchant_city}")
    except Exception as e:
        print(f"  ❌ Failed to load config: {e}")
        return False
    
    # Step 3: Instantiate QR Service and generate test QR
    print("\n[3/5] Generating test QR code...")
    try:
        from backend.bakong import BakongQRService
        qr_service = BakongQRService(config)
        
        # Generate a test QR
        test_bill_number = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        qr_result = qr_service.generate_qr(
            amount=1.00,
            currency="USD",
            bill_number=test_bill_number,
            description="Phase 1 sanity check",
            phone_number="012345678"
        )
        
        if not qr_result:
            print(f"  ❌ QR generation returned None")
            return False
        
        print(f"  ✓ QR generated successfully")
        print(f"    - Bill number: {test_bill_number}")
        print(f"    - Amount: {qr_result.get('amount')} {qr_result.get('currency')}")
        print(f"    - QR String length: {len(qr_result.get('qr_string', ''))} chars")
        print(f"    - QR MD5: {qr_result.get('qr_md5')}")
        
        # Validate QR string format
        qr_string = qr_result.get('qr_string', '')
        if not qr_string or len(qr_string) < 50:
            print(f"  ⚠️  Warning: QR string seems short ({len(qr_string)} chars)")
        
        # Validate MD5 format (should be 32 hex chars)
        qr_md5 = qr_result.get('qr_md5', '')
        if not qr_md5 or len(qr_md5) != 32:
            print(f"  ❌ MD5 format invalid: expected 32 chars, got {len(qr_md5)}")
            return False
        
        if not all(c in '0123456789abcdef' for c in qr_md5):
            print(f"  ❌ MD5 contains invalid characters")
            return False
        
        print(f"  ✓ MD5 format valid (32 hex characters)")
        
        # Store for next step
        test_md5 = qr_md5
        
    except Exception as e:
        print(f"  ❌ QR generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Instantiate Payment Service
    print("\n[4/5] Instantiating Payment Service...")
    try:
        from backend.bakong import BakongPaymentService
        payment_service = BakongPaymentService(config)
        print(f"  ✓ Payment service instantiated")
    except Exception as e:
        print(f"  ❌ Failed to instantiate payment service: {e}")
        return False
    
    # Step 5: Check payment status
    print("\n[5/5] Checking payment status via Bakong API...")
    try:
        status = payment_service.check_payment_status(test_md5)
        
        if status is None:
            print(f"  ❌ Payment check returned None")
            return False
        
        print(f"  ✓ Payment status retrieved: {status}")
        
        if status not in ["PAID", "UNPAID"]:
            print(f"  ⚠️  Warning: Unexpected status value: {status}")
            print(f"     Expected 'PAID' or 'UNPAID'")
        
        # Expected: UNPAID (since we just generated it)
        if status == "UNPAID":
            print(f"  ✓ Status is UNPAID (expected for new QR)")
        else:
            print(f"  ⚠️  Status is {status} (expected UNPAID for new QR)")
        
    except Exception as e:
        print(f"  ❌ Payment status check failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Test QR MD5:          {test_md5}")
    print(f"Test QR String:       {qr_result.get('qr_string', '')[:50]}...")
    print(f"Payment Status:       {status}")
    print("\n✓ All Phase 1 checks passed!")
    print("\nNext steps:")
    print("  1. Review data formats above")
    print("  2. Verify QR string and MD5 formats are expected")
    print("  3. Proceed to Phase 2 (Database schema)")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_phase1()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
