# Bakong Payment Status Handling - Critical for Phase 3

## Problem: Distinguishing Payment States

Phase 3 endpoints must correctly handle four different payment scenarios:

| Scenario | SDK Returns | What It Means | Phase 3 Action |
|----------|------------|--------------|----------------|
| **PAID** | "PAID" | Payment received & confirmed by Bakong | Mark VERIFIED, update Client.last_payment |
| **UNPAID** | "UNPAID" | QR exists but not yet paid by customer | Keep PENDING, continue polling |
| **NOT_FOUND** | None or "NOT_FOUND" | QR not recognized (expired or invalid) | Keep PENDING, check Payment.expires_at |
| **ERROR** | Exception or None | Network/API error (transient) | DO NOT mark FAILED, retry later |

## Critical: UNPAID ≠ FAILED

**IMPORTANT**: If a payment verification returns UNPAID or NOT_FOUND, you must:
- ❌ NOT mark the Payment as FAILED
- ❌ NOT update Client.last_payment yet
- ✅ Keep Payment as PENDING
- ✅ Continue polling at regular intervals

Only transition from PENDING to VERIFIED when status is PAID.

## Return Value Formats

### `check_payment_status(md5_hash)` - Low-level

Returns just the status string:
```python
status = payment_service.check_payment_status(md5_hash)

# Possible returns:
# "PAID"      → Payment confirmed
# "UNPAID"    → Waiting for payment
# "NOT_FOUND" → QR not found (may be expired)
# None        → Error (network, API, etc.)
```

**Phase 3 Usage**: Use this for simple checks, but handle all four cases.

### `verify_payment(md5_hash)` - Recommended for Phase 3

Returns structured response with full context:
```python
result = payment_service.verify_payment(md5_hash)

# Returns:
{
    "verified": False,              # True only if PAID
    "status": "PAID|UNPAID|NOT_FOUND|ERROR",
    "payment_data": {...},          # Full transaction details if PAID
    "error": None or "message",     # Error description if status is ERROR
    "timestamp": "2026-04-19T..."
}
```

**Phase 3 Usage**: Recommended method for the `/customer/payment/verify` endpoint.

## Phase 3 Endpoint Logic (Pseudocode)

```python
@router.post("/customer/payment/verify")
@limiter.limit("10/minute")  # Strict rate limit
async def verify_payment(payment_id: int, db: Session):
    # 1. Look up payment record
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        return {"error": "Payment not found"}, 404
    
    # 2. Check if already verified
    if payment.payment_status == "VERIFIED":
        return {"status": "VERIFIED", "message": "Already paid"}
    
    # 3. Check if expired
    if payment.expires_at < datetime.utcnow():
        payment.payment_status = "EXPIRED"
        db.commit()
        return {"status": "EXPIRED", "message": "QR expired, generate new one"}
    
    # 4. Verify with Bakong
    result = payment_service.verify_payment(payment.qr_md5_hash)
    
    # 5. Handle each status
    if result["status"] == "PAID":
        # SUCCESS - Mark verified and update client
        payment.payment_status = "VERIFIED"
        payment.bakong_transaction_hash = result["payment_data"]["hash"]
        payment.verified_at = datetime.utcnow()
        
        client = db.query(Client).filter(Client.id == payment.client_id).first()
        client.last_payment = date.today()
        
        db.commit()
        return {"verified": True, "status": "VERIFIED"}
    
    elif result["status"] == "UNPAID":
        # PENDING - Still waiting, keep polling
        return {"verified": False, "status": "UNPAID", 
                "message": "Payment not yet received, keep waiting"}
    
    elif result["status"] == "NOT_FOUND":
        # NOT FOUND - QR might be expired
        if payment.expires_at < datetime.utcnow():
            payment.payment_status = "EXPIRED"
            db.commit()
            return {"verified": False, "status": "EXPIRED"}
        else:
            # Not yet expired, Bakong might not have synced yet
            return {"verified": False, "status": "PENDING",
                    "message": "QR not yet recognized by Bakong"}
    
    else:  # ERROR
        # DO NOT UPDATE STATUS - Keep PENDING
        # Error is transient (network, API down, etc.)
        return {
            "verified": False,
            "status": "ERROR",
            "message": result.get("error", "Could not verify payment"),
            "retry": True
        }, 503  # Service Unavailable
```

## Key Takeaways for Phase 3

1. **Always handle all four cases** (PAID, UNPAID, NOT_FOUND, ERROR)
2. **Never mark PENDING as FAILED** unless explicitly expired
3. **Errors are transient** - return 503 Service Unavailable, don't mark as failed
4. **Use `verify_payment()`** for structured response with full context
5. **Rate limit strictly** - `/customer/payment/verify` is a poll endpoint (abuse target)
6. **Check `Payment.expires_at`** when status is NOT_FOUND to determine true expiration

## Testing

When testing Phase 3:

1. Generate a test QR with `test_bakong_phase1.py`
2. Manually verify it returns "UNPAID"
3. In Phase 3, poll it and verify it stays UNPAID until actually paid
4. Create another QR and have someone scan and pay it
5. Verify polling detects the payment and marks VERIFIED
6. Test timeout/expiration handling
