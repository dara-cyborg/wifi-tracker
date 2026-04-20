import os
import logging
import pytz
from typing import Optional, Dict, Any, List
from bakong_khqr import KHQR

logger = logging.getLogger(__name__)
CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')


class BakongConfig:
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
        try:
            result = self.khqr.qr_image(qr_string, output_path=output_path, format=format)
            
            if result is None:
                logger.error(f"QR image generation returned None for format={format}")
                return None
            
            if isinstance(result, str):
                if result.startswith("data:"):
                    return result
                elif len(result) > 100:
                    return f"data:image/png;base64,{result}"
                else:
                    if os.path.exists(result):
                        with open(result, 'rb') as f:
                            image_bytes = f.read()
                        base64_data = __import__('base64').b64encode(image_bytes).decode('utf-8')
                        return f"data:image/png;base64,{base64_data}"
            
            elif isinstance(result, bytes):
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
        try:
            deeplink = self.khqr.generate_deeplink(
                qr_string,
                callback=callback_url,
                appIconUrl=app_icon_url,
                appName=app_name
            )
            return deeplink if deeplink else None
                
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
                else:
                    result["status"] = "ERROR"
                    result["error"] = "Payment marked as PAID but details could not be retrieved"
                    
            elif status == "UNPAID":
                result["status"] = "UNPAID"
                
            elif status == "NOT_FOUND":
                result["status"] = "NOT_FOUND"
                
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in verify_payment: {e}")
            result["status"] = "ERROR"
            result["error"] = f"Unexpected error: {str(e)}"
            return result
    
    def check_payment_status(self, md5_hash: str) -> Optional[str]:
        """
        Returns PAID/UNPAID/NOT_FOUND so caller can decide next action.
        Returns None on transient errors (network issues, API down).
        """
        try:
            status = self.khqr.check_payment(md5_hash)
            
            if status is None:
                return "NOT_FOUND"
            
            status = str(status).upper()
            
            if status in ["PAID", "UNPAID", "NOT_FOUND"]:
                return status
            else:
                return None
            
        except Exception:
            return None
    
    def get_payment_details(self, md5_hash: str) -> Optional[Dict[str, Any]]:
        try:
            payment_info = self.khqr.get_payment(md5_hash)
            
            if payment_info:
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
            return None
                
        except Exception:
            return None
    
    def check_bulk_payments(self, md5_list: List[str]) -> Optional[List[str]]:
        try:
            if len(md5_list) > 50:
                return None
            
            paid_md5_list = self.khqr.check_bulk_payments(md5_list)
            return paid_md5_list
            
        except Exception:
            return None
