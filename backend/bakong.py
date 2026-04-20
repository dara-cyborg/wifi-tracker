import os
import logging
import pytz
from typing import Optional, Dict, Any, List
from bakong_khqr import KHQR

logger = logging.getLogger(__name__)
CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')


class BakongConfig:
    """Load and validate Bakong configuration from environment"""
    
    KHQR_NAME_MAX_LENGTH = 13
    
    def __init__(self):
        self.token = os.getenv("BAKONG_DEVELOPER_TOKEN")
        self.merchant_account = os.getenv("BAKONG_MERCHANT_ACCOUNT_ID")
        self.merchant_name = os.getenv("BAKONG_MERCHANT_NAME")
        self.merchant_city = os.getenv("BAKONG_MERCHANT_CITY")
        
        if not self.token:
            raise ValueError("BAKONG_DEVELOPER_TOKEN environment variable not set")
        if not self.merchant_account:
            raise ValueError("BAKONG_MERCHANT_ACCOUNT_ID environment variable not set")
        
        logger.info(f"Bakong config loaded: {self.merchant_account}")


class BakongService:
    """Unified Bakong KHQR service for QR generation and payment verification"""
    
    def __init__(self, config: BakongConfig):
        self.config = config
        self.khqr = KHQR(config.token)
    
    def generate_qr(
        self,
        amount: float,
        currency: str = "USD",
        bill_number: str = "",
        description: str = "",
        phone_number: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Generate KHQR QR code for payment
        
        Args:
            amount: Payment amount
            currency: Currency code (USD or KHR)
            bill_number: Invoice/bill reference number
            description: Payment description
            phone_number: Optional phone number
            
        Returns:
            Dict with qr_string and qr_md5 or None on error
        """
        try:
            if currency not in ["USD", "KHR"]:
                logger.error(f"Invalid currency: {currency}")
                return None
            
            merchant_name = os.getenv("BAKONG_MERCHANT_NAME", "WiFi Tracker")[:self.config.KHQR_NAME_MAX_LENGTH]
            
            qr_string = self.khqr.create_qr(
                bank_account=self.config.merchant_account,
                merchant_name=merchant_name,
                merchant_city=self.config.merchant_city,
                amount=amount,
                currency=currency,
                store_label=self.config.merchant_name,
                bill_number=bill_number,
                phone_number=phone_number,
                terminal_label="WiFiTracker",
                static=False,
                expiration=1
            )
            
            if not qr_string:
                logger.error("Failed to generate QR string")
                return None
            
            qr_md5 = self.khqr.generate_md5(qr_string)
            
            logger.info(f"QR generated successfully for {bill_number}: {qr_md5}")
            
            return {
                "qr_string": qr_string,
                "qr_md5": qr_md5,
                "amount": amount,
                "currency": currency,
                "bill_number": bill_number,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Error generating KHQR: {e}")
            return None
    
    def generate_qr_image(
        self,
        qr_string: str,
        output_path: Optional[str] = None,
        format: str = "base64_uri"
    ) -> Optional[str]:
        """
        Generate QR code image from QR string
        
        Args:
            qr_string: QR string from create_qr()
            output_path: Optional path to save image (only used for png/jpeg/webp formats)
            format: Image format ('png', 'jpeg', 'webp', 'bytes', 'base64', 'base64_uri')
                   Default: 'base64_uri' to get data URI for frontend display
            
        Returns:
            Base64 data URI string (data:image/png;base64,...) or None on error
        """
        try:
            result = self.khqr.qr_image(qr_string, output_path=output_path, format=format)
            
            if result is None:
                logger.error(f"QR image generation returned None for format={format}")
                return None
            
            if isinstance(result, str):
                if result.startswith("data:"):
                    logger.info(f"QR image generated successfully (data URI format)")
                    return result
                elif len(result) > 100:
                    logger.warning(f"QR image is base64 but not in data URI format, wrapping...")
                    return f"data:image/png;base64,{result}"
                else:
                    logger.warning(f"QR image might be file path: {result[:50]}...")
                    if os.path.exists(result):
                        with open(result, 'rb') as f:
                            image_bytes = f.read()
                        base64_data = __import__('base64').b64encode(image_bytes).decode('utf-8')
                        return f"data:image/png;base64,{base64_data}"
            
            elif isinstance(result, bytes):
                logger.info("QR image returned as bytes, converting to base64 data URI")
                base64_data = __import__('base64').b64encode(result).decode('utf-8')
                return f"data:image/png;base64,{base64_data}"
            
            logger.error(f"Unexpected return type from qr_image: {type(result)}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating QR image: {e}", exc_info=True)
            return None
    
    def generate_deeplink(
        self,
        qr_string: str,
        callback_url: str,
        app_icon_url: str = "",
        app_name: str = "DARAMONGKOL"
    ) -> Optional[str]:
        """
        Generate Bakong deeplink for payment
        
        Args:
            qr_string: QR string from create_qr()
            callback_url: URL to redirect to after payment
            app_icon_url: Your app's icon URL
            app_name: Display name of your app
            
        Returns:
            Deeplink URL or None on error
        """
        try:
            deeplink = self.khqr.generate_deeplink(
                qr_string,
                callback=callback_url,
                appIconUrl=app_icon_url,
                appName=app_name
            )
            
            if deeplink:
                logger.info(f"Deeplink generated successfully")
                return deeplink
            else:
                logger.error("Failed to generate deeplink")
                return None
                
        except Exception as e:
            logger.error(f"Error generating deeplink: {e}")
            return None

    def verify_payment(self, md5_hash: str) -> Dict[str, Any]:
        from datetime import datetime
        
        result = {
            "verified": False,
            "status": "ERROR",
            "payment_data": None,
            "error": None,
            "timestamp": datetime.now(CAMBODIA_TZ).isoformat()
        }
        
        try:
            status = self.check_payment_status(md5_hash)
            
            if status is None:
                result["status"] = "ERROR"
                result["error"] = "Failed to check payment status (network or API error)"
                return result
            
            result["status"] = status
            
            if status == "PAID":
                payment_info = self.get_payment_details(md5_hash)
                if payment_info:
                    result["verified"] = True
                    result["payment_data"] = payment_info
                    logger.info(f"Payment VERIFIED for {md5_hash}")
                else:
                    result["status"] = "ERROR"
                    result["error"] = "Payment marked as PAID but details could not be retrieved"
                    logger.error(f"Inconsistent state: PAID but no details for {md5_hash}")
                    
            elif status == "UNPAID":
                logger.info(f"Payment UNPAID for {md5_hash} (waiting for customer)")
                result["status"] = "UNPAID"
                
            elif status == "NOT_FOUND":
                logger.warning(f"Payment NOT_FOUND for {md5_hash} (may be expired)")
                result["status"] = "NOT_FOUND"
                
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}")
            result["status"] = "ERROR"
            result["error"] = f"Unexpected error: {str(e)}"
            return result
    
    def check_payment_status(self, md5_hash: str) -> Optional[str]:
        """
        Check if payment has been received for a QR
        
        CRITICAL for Phase 3: This method must distinguish between:
        - "PAID": Payment received and confirmed
        - "UNPAID": QR exists but not yet paid (keep waiting)
        - "NOT_FOUND": QR MD5 not recognized by Bakong (QR might be expired or invalid)
        - None: Error occurred (network, API, etc.)
        
        Args:
            md5_hash: MD5 hash of the QR string
            
        Returns:
            "PAID", "UNPAID", "NOT_FOUND", or None on error
            
        Phase 3 Logic:
        - PAID → Mark Payment as VERIFIED, update Client.last_payment
        - UNPAID → Keep Payment as PENDING, continue polling
        - NOT_FOUND → Keep PENDING, but may indicate QR expired (check Payment.expires_at)
        - None → Retry later, don't mark as failed
        """
        try:
            status = self.khqr.check_payment(md5_hash)
            
            # Explicit handling of different status values
            if status is None:
                logger.warning(f"Payment check returned None for {md5_hash} (may indicate NOT_FOUND)")
                return "NOT_FOUND"
            
            # SDK should return string status
            status = str(status).upper()
            
            if status in ["PAID", "UNPAID", "NOT_FOUND"]:
                logger.info(f"Payment status for {md5_hash}: {status}")
                return status
            else:
                logger.warning(f"Unexpected status value for {md5_hash}: {status}")
                # Treat unknown status as error, not as failure
                return None
            
        except Exception as e:
            logger.error(f"Error checking payment status for {md5_hash}: {e}")
            # Return None on error - Phase 3 should NOT mark as FAILED
            # Errors are transient (network, API down, etc.)
            return None
    
    def get_payment_details(self, md5_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full payment transaction details
        
        Args:
            md5_hash: MD5 hash of the QR string
            
        Returns:
            Dict with transaction data or None on error
        """
        try:
            payment_info = self.khqr.get_payment(md5_hash)
            
            if payment_info:
                logger.info(f"Payment details retrieved for {md5_hash}")
                return {
                    "hash": payment_info.get("hash"),
                    "from_account": payment_info.get("fromAccountId"),
                    "to_account": payment_info.get("toAccountId"),
                    "amount": payment_info.get("amount"),
                    "currency": payment_info.get("currency"),
                    "description": payment_info.get("description"),
                    "created_at": payment_info.get("createdDateMs"),
                    "acknowledged_at": payment_info.get("acknowledgedDateMs"),
                    "tracking_status": payment_info.get("trackingStatus"),
                    "receiver_bank": payment_info.get("receiverBank"),
                    "external_ref": payment_info.get("externalRef")
                }
            else:
                logger.warning(f"No payment info found for {md5_hash}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving payment details: {e}")
            return None
    
    def check_bulk_payments(self, md5_list: List[str]) -> Optional[List[str]]:
        """
        Check payment status for multiple QRs (max 50)
        
        Args:
            md5_list: List of MD5 hashes (max 50)
            
        Returns:
            List of MD5s that have been paid, or None on error
        """
        try:
            if len(md5_list) > 50:
                logger.error(f"MD5 list exceeds 50 limit: {len(md5_list)}")
                return None
            
            paid_md5_list = self.khqr.check_bulk_payments(md5_list)
            logger.info(f"Bulk payment check: {len(paid_md5_list)} paid out of {len(md5_list)}")
            return paid_md5_list
            
        except Exception as e:
            logger.error(f"Error checking bulk payments: {e}")
            return None
