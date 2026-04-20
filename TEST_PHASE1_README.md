# Phase 1 Test Instructions

## Before Running the Test

Make sure your `.env` file has these variables set:

```
BAKONG_DEVELOPER_TOKEN=your-actual-token-here
BAKONG_MERCHANT_ACCOUNT_ID=username@bank
BAKONG_MERCHANT_NAME=WiFi Tracker
BAKONG_MERCHANT_CITY=Phnom Penh
```

## Running the Test

From the project root directory:

```bash
python test_bakong_phase1.py
```

## What the Test Does

1. **Checks environment variables** - Verifies credentials are set
2. **Loads Bakong config** - Ensures configuration loads without errors
3. **Generates a test QR** - Creates a QR with:
   - Amount: $1.00 USD
   - Bill number: `TEST-{timestamp}`
   - Phone: 012345678
4. **Validates QR format**:
   - QR string should be 50+ characters
   - MD5 should be exactly 32 hex characters
5. **Checks payment status** - Calls Bakong API to check if QR has been paid
   - Should return "UNPAID" (it's a fresh QR)

## Expected Output

```
================================================================================
BAKONG KHQR INTEGRATION - PHASE 1 SANITY CHECK
================================================================================

[1/5] Checking environment variables...
  ✓ Token present: eyJ0eXAiOiJKV1QiLC...
  ✓ Merchant account: username@ababank

[2/5] Loading Bakong configuration...
  ✓ Config loaded successfully
    - Token: eyJ0eXAiOiJKV1QiLC...
    - Merchant: username@ababank
    - Name: WiFi Tracker
    - City: Phnom Penh

[3/5] Generating test QR code...
  ✓ QR generated successfully
    - Bill number: TEST-20260419123456
    - Amount: 1.0 USD
    - QR String length: 138 chars
    - QR MD5: d1b4a6e8f2c9e5a3b7c1d4e8f2a5b9c3

[4/5] Instantiating Payment Service...
  ✓ Payment service instantiated

[5/5] Checking payment status via Bakong API...
  ✓ Payment status retrieved: UNPAID
  ✓ Status is UNPAID (expected for new QR)

================================================================================
RESULTS
================================================================================
Test QR MD5:          d1b4a6e8f2c9e5a3b7c1d4e8f2a5b9c3
Test QR String:       00020101021229180014username@ababank5204599953...
Payment Status:       UNPAID

✓ All Phase 1 checks passed!

Next steps:
  1. Review data formats above
  2. Verify QR string and MD5 formats are expected
  3. Proceed to Phase 2 (Database schema)
================================================================================
```

## Troubleshooting

If you get errors:

### `BAKONG_DEVELOPER_TOKEN not set`
- Add the variable to your `.env` file
- Make sure you're running from the project root directory
- Python-dotenv should auto-load the `.env` file

### `Failed to generate QR`
- Check your token is valid
- Check your merchant account ID format (should be `username@bank`)
- Check your internet connection
- The Bakong API might be down

### `Payment status check failed`
- The MD5 might not be recognized immediately
- Try waiting a few seconds and running again
- Check Bakong API is accessible

## Next: Phase 2

Once all checks pass:
1. Review the output formats
2. Note the MD5 format (32 hex chars)
3. Note the QR string format
4. Proceed to Phase 2 to create the Payment database table
