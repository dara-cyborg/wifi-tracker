# Bakong KHQR Integration - Environment Variables

This file documents the required environment variables for Bakong KHQR integration using the `bakong-khqr` SDK.

## Required Variables

### Bakong Configuration

```
# Your Bakong Developer Token (get from https://api-bakong.nbc.gov.kh/register/)
BAKONG_DEVELOPER_TOKEN=your-developer-token-here

# Your Bakong merchant account ID (format: username@bank)
# Example: myshop@ababank
# Get this from your Bakong Mobile App under Profile
BAKONG_MERCHANT_ACCOUNT_ID=your-account@bank

# Display name for your business (shown in QR payments)
BAKONG_MERCHANT_NAME=WiFi Tracker

# City where your merchant is located (optional)
BAKONG_MERCHANT_CITY=Phnom Penh

```

## Setup Instructions

1. **Register with NBC (Bakong)**
   - Visit https://api-bakong.nbc.gov.kh/register/
   - Register your business/merchant account
   - Get your Developer Token and Merchant Account ID
   - Note: Account must have full KYC verification

2. **Add to your .env file**
   ```
   BAKONG_DEVELOPER_TOKEN=your-token-from-registration
   BAKONG_MERCHANT_ACCOUNT_ID=username@bank
   BAKONG_MERCHANT_NAME=Your Business Name
   BAKONG_MERCHANT_CITY=Phnom Penh
   ```

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
   This will install `bakong-khqr` which provides the KHQR SDK.

4. **Test the integration**
   - The app will attempt to initialize Bakong services on startup
   - Check logs for "Bakong services initialized successfully"
   - If you see initialization errors, verify your credentials

## API Features (bakong-khqr SDK)

The bakong-khqr package provides the following operations:

- **QR Generation**: `generate_qr()` - Create payment QRs with amount, description, etc.
- **MD5 Hash**: `generate_md5()` - Generate MD5 hash of QR string for transaction verification
- **Payment Check**: `check_payment()` - Returns "PAID" or "UNPAID" status
- **Payment Details**: `get_payment()` - Retrieve full transaction information
- **Bulk Check**: `check_bulk_payments()` - Check up to 50 QRs at once
- **QR Image**: `qr_image()` - Generate QR code images (PNG, JPEG, WebP, Base64)
- **Deeplink**: `generate_deeplink()` - Generate Bakong payment deeplinks

## Environment (Production vs Sandbox)

Both use the same API endpoint. Differentiation is via your token credentials:

- **Production**: Use your production token from NBC
- **Sandbox/Testing**: Use sandbox credentials from NBC (if available)

## Phase 1 Complete ✓

With Phase 1 complete, you have:
- ✓ bakong-khqr SDK installed
- ✓ Bakong service module with QR generation
- ✓ Payment verification functions ready
- ✓ Automatic error handling and logging

Proceed to Phase 2 when ready (Database schema updates).

