import requests
import json
import logging
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .strategies import PaymentStrategy

logger = logging.getLogger(__name__)

class BkashStrategy(PaymentStrategy):
    def __init__(self):
        self.base_url = settings.BKASH_BASE_URL
        self.app_key = settings.BKASH_APP_KEY
        self.app_secret = settings.BKASH_APP_SECRET
        self.username = settings.BKASH_USERNAME
        self.password = settings.BKASH_PASSWORD
        self.token_key = 'bkash_access_token'
        self.refresh_token_key = 'bkash_refresh_token'
    
    def get_provider_name(self):
        return 'bkash'
    
    def _get_token(self, force_refresh=False):
        """Get bKash access token with caching"""
        if not force_refresh:
            token = cache.get(self.token_key)
            if token:
                return token
        
        try:
            # First, get a token
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/token/grant",
                json={
                    'app_key': self.app_key,
                    'app_secret': self.app_secret
                },
                headers={
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"bKash token response status: {response.status_code}")
            
            if response.status_code != 200:
                raise ValidationError(f"bKash token request failed with status {response.status_code}")
            
            data = response.json()
            logger.info(f"bKash token response: {json.dumps(data, indent=2)}")
            
            if data.get('statusCode') != '0000':
                raise ValidationError(f"bKash token failed: {data.get('statusMessage', 'Unknown error')}")
            
            # Cache token for 55 minutes (tokens expire in 1 hour)
            token = data.get('id_token')
            refresh_token = data.get('refresh_token')
            
            if token:
                cache.set(self.token_key, token, timeout=3300)  # 55 minutes
                if refresh_token:
                    cache.set(self.refresh_token_key, refresh_token, timeout=3300)
                return token
            else:
                raise ValidationError("No token received from bKash")
            
        except requests.RequestException as e:
            logger.error(f"bKash token generation network error: {str(e)}")
            raise ValidationError(f"bKash token generation failed: Network error - {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"bKash token response parse error: {str(e)}")
            raise ValidationError(f"bKash token generation failed: Invalid response format")
        except Exception as e:
            logger.error(f"bKash token generation error: {str(e)}")
            raise ValidationError(f"bKash token generation failed: {str(e)}")
    
    def _refresh_token(self):
        """Refresh bKash token"""
        refresh_token = cache.get(self.refresh_token_key)
        if not refresh_token:
            return self._get_token(force_refresh=True)
        
        try:
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/token/refresh",
                json={
                    'app_key': self.app_key,
                    'app_secret': self.app_secret,
                    'refresh_token': refresh_token
                },
                headers={
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return self._get_token(force_refresh=True)
            
            data = response.json()
            
            if data.get('statusCode') != '0000':
                return self._get_token(force_refresh=True)
            
            token = data.get('id_token')
            if token:
                cache.set(self.token_key, token, timeout=3300)
                return token
            else:
                return self._get_token(force_refresh=True)
            
        except Exception:
            return self._get_token(force_refresh=True)
    
    def create_payment(self, order, payment_data=None):
        """Create bKash payment"""
        try:
            token = self._get_token()
            
            # Prepare request data
            request_data = {
                'mode': '0011',
                'payerReference': str(order.user.id)[:20],
                'callbackURL': f"{settings.FRONTEND_URL}/payment/callback?order_id={order.id}",
                'amount': str(float(order.total_amount)),
                'currency': 'BDT',
                'intent': 'sale',
                'merchantInvoiceNumber': order.order_number[:40]
            }
            
            logger.info(f"bKash create payment request: {json.dumps(request_data, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/create",
                json=request_data,
                headers={
                    'Authorization': token,
                    'X-APP-Key': self.app_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"bKash create payment response status: {response.status_code}")
            
            if response.status_code != 200:
                # Try refreshing token and retry
                token = self._refresh_token()
                response = requests.post(
                    f"{self.base_url}/tokenized/checkout/create",
                    json=request_data,
                    headers={
                        'Authorization': token,
                        'X-APP-Key': self.app_key,
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise ValidationError(f"bKash create payment failed with status {response.status_code}")
            
            data = response.json()
            logger.info(f"bKash create payment response: {json.dumps(data, indent=2)}")
            
            if data.get('statusCode') != '0000':
                raise ValidationError(f"bKash create failed: {data.get('statusMessage', 'Unknown error')}")
            
            return {
                'payment_id': data.get('paymentID'),
                'checkout_url': data.get('bkashURL'),
                'provider': 'bkash',
                'status': 'pending',
                'transaction_id': data.get('paymentID'),
                'amount': float(order.total_amount),
                'currency': 'BDT',
                'payer_reference': request_data['payerReference'],
                'merchant_invoice': request_data['merchantInvoiceNumber']
            }
            
        except requests.RequestException as e:
            logger.error(f"bKash payment creation network error: {str(e)}")
            raise ValidationError(f"bKash payment creation failed: Network error - {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"bKash payment creation response parse error: {str(e)}")
            raise ValidationError(f"bKash payment creation failed: Invalid response format")
        except Exception as e:
            logger.error(f"bKash payment creation error: {str(e)}")
            raise ValidationError(f"bKash payment creation failed: {str(e)}")
    
    def confirm_payment(self, payment, data=None):
        """Execute/Confirm bKash payment"""
        try:
            token = self._get_token()
            
            # Execute payment
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/execute",
                json={
                    'paymentID': payment.transaction_id
                },
                headers={
                    'Authorization': token,
                    'X-APP-Key': self.app_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"bKash execute payment response status: {response.status_code}")
            
            if response.status_code != 200:
                token = self._refresh_token()
                response = requests.post(
                    f"{self.base_url}/tokenized/checkout/execute",
                    json={
                        'paymentID': payment.transaction_id
                    },
                    headers={
                        'Authorization': token,
                        'X-APP-Key': self.app_key,
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise ValidationError(f"bKash execute failed with status {response.status_code}")
            
            data = response.json()
            logger.info(f"bKash execute payment response: {json.dumps(data, indent=2)}")
            
            if data.get('statusCode') != '0000':
                # Check if payment is already completed
                if data.get('statusCode') == '2001':  # Already completed
                    return {
                        'status': 'success',
                        'transaction_id': data.get('trxID', payment.transaction_id),
                        'provider': 'bkash',
                        'payment_id': payment.transaction_id,
                        'amount': float(payment.amount)
                    }
                raise ValidationError(f"bKash execute failed: {data.get('statusMessage', 'Unknown error')}")
            
            return {
                'status': 'success' if data.get('transactionStatus') == 'Completed' else 'pending',
                'transaction_id': data.get('trxID', payment.transaction_id),
                'provider': 'bkash',
                'payment_id': payment.transaction_id,
                'amount': float(data.get('amount', payment.amount))
            }
            
        except requests.RequestException as e:
            logger.error(f"bKash confirmation network error: {str(e)}")
            raise ValidationError(f"bKash confirmation failed: Network error - {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"bKash confirmation response parse error: {str(e)}")
            raise ValidationError(f"bKash confirmation failed: Invalid response format")
        except Exception as e:
            logger.error(f"bKash confirmation error: {str(e)}")
            raise ValidationError(f"bKash confirmation failed: {str(e)}")
    
    def verify_payment(self, payment):
        """Verify bKash payment status"""
        try:
            token = self._get_token()
            
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/payment/status",
                json={
                    'paymentID': payment.transaction_id
                },
                headers={
                    'Authorization': token,
                    'X-APP-Key': self.app_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"bKash verify payment response status: {response.status_code}")
            
            if response.status_code != 200:
                token = self._refresh_token()
                response = requests.post(
                    f"{self.base_url}/tokenized/checkout/payment/status",
                    json={
                        'paymentID': payment.transaction_id
                    },
                    headers={
                        'Authorization': token,
                        'X-APP-Key': self.app_key,
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    return {
                        'status': 'pending',
                        'transaction_id': payment.transaction_id,
                        'provider': 'bkash',
                        'payment_id': payment.transaction_id,
                        'error': f"Status check failed with status {response.status_code}"
                    }
            
            data = response.json()
            logger.info(f"bKash verify payment response: {json.dumps(data, indent=2)}")
            
            if data.get('statusCode') != '0000':
                return {
                    'status': 'pending',
                    'transaction_id': payment.transaction_id,
                    'provider': 'bkash',
                    'payment_id': payment.transaction_id,
                    'error': data.get('statusMessage', 'Unknown error')
                }
            
            return {
                'status': 'success' if data.get('transactionStatus') == 'Completed' else 'pending',
                'transaction_id': data.get('trxID', payment.transaction_id),
                'provider': 'bkash',
                'payment_id': payment.transaction_id,
                'amount': float(data.get('amount', payment.amount)),
                'currency': data.get('currency', 'BDT'),
                'reference': data.get('reference'),
                'payer_reference': data.get('payerReference')
            }
            
        except requests.RequestException as e:
            logger.error(f"bKash verification network error: {str(e)}")
            return {
                'status': 'pending',
                'transaction_id': payment.transaction_id,
                'provider': 'bkash',
                'payment_id': payment.transaction_id,
                'error': f"Network error: {str(e)}"
            }
        except json.JSONDecodeError as e:
            logger.error(f"bKash verification response parse error: {str(e)}")
            return {
                'status': 'pending',
                'transaction_id': payment.transaction_id,
                'provider': 'bkash',
                'payment_id': payment.transaction_id,
                'error': f"Invalid response format: {str(e)}"
            }
        except Exception as e:
            logger.error(f"bKash verification error: {str(e)}")
            return {
                'status': 'pending',
                'transaction_id': payment.transaction_id,
                'provider': 'bkash',
                'payment_id': payment.transaction_id,
                'error': str(e)
            }
    
    def handle_webhook(self, payload, signature):
        """Handle bKash webhook"""
        try:
            # bKash webhook payload
            data = payload if isinstance(payload, dict) else json.loads(payload)
            logger.info(f"bKash webhook received: {json.dumps(data, indent=2)}")
            
            # Check if it's a successful payment notification
            if data.get('statusCode') == '0000':
                # bKash sends a callback with payment status
                if data.get('transactionStatus') == 'Completed':
                    return {
                        'event': 'payment.success',
                        'transaction_id': data.get('trxID'),
                        'status': 'success',
                        'order_id': data.get('merchantInvoiceNumber'),
                        'payment_id': data.get('paymentID'),
                        'metadata': data
                    }
                elif data.get('transactionStatus') == 'Failed':
                    return {
                        'event': 'payment.failed',
                        'transaction_id': data.get('paymentID'),
                        'status': 'failed',
                        'order_id': data.get('merchantInvoiceNumber'),
                        'payment_id': data.get('paymentID'),
                        'metadata': data
                    }
                else:
                    return {
                        'event': 'payment.pending',
                        'transaction_id': data.get('paymentID'),
                        'status': 'pending',
                        'order_id': data.get('merchantInvoiceNumber'),
                        'payment_id': data.get('paymentID'),
                        'metadata': data
                    }
            elif data.get('statusCode') == '2001':
                # Payment already processed
                return {
                    'event': 'payment.already_processed',
                    'transaction_id': data.get('trxID'),
                    'status': 'success',
                    'order_id': data.get('merchantInvoiceNumber'),
                    'payment_id': data.get('paymentID'),
                    'metadata': data
                }
            else:
                return {
                    'event': 'payment.error',
                    'status': 'failed',
                    'payment_id': data.get('paymentID'),
                    'metadata': data,
                    'error': data.get('statusMessage', 'Unknown error')
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"bKash webhook JSON parse error: {str(e)}")
            return {
                'event': 'webhook.error',
                'status': 'failed',
                'error': f"Invalid JSON: {str(e)}"
            }
        except Exception as e:
            logger.error(f"bKash webhook handling error: {str(e)}")
            return {
                'event': 'webhook.error',
                'status': 'failed',
                'error': str(e)
            }
    
    def refund_payment(self, payment, amount=None, reason=None):
        """Refund a bKash payment"""
        try:
            token = self._get_token()
            
            refund_amount = str(float(amount if amount else payment.amount))
            refund_reason = reason or 'Customer requested refund'
            
            response = requests.post(
                f"{self.base_url}/tokenized/checkout/payment/refund",
                json={
                    'paymentID': payment.transaction_id,
                    'amount': refund_amount,
                    'reason': refund_reason,
                    'merchantInvoiceNumber': f"REF_{payment.order.order_number}"
                },
                headers={
                    'Authorization': token,
                    'X-APP-Key': self.app_key,
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"bKash refund response status: {response.status_code}")
            
            if response.status_code != 200:
                token = self._refresh_token()
                response = requests.post(
                    f"{self.base_url}/tokenized/checkout/payment/refund",
                    json={
                        'paymentID': payment.transaction_id,
                        'amount': refund_amount,
                        'reason': refund_reason,
                        'merchantInvoiceNumber': f"REF_{payment.order.order_number}"
                    },
                    headers={
                        'Authorization': token,
                        'X-APP-Key': self.app_key,
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise ValidationError(f"bKash refund failed with status {response.status_code}")
            
            data = response.json()
            logger.info(f"bKash refund response: {json.dumps(data, indent=2)}")
            
            if data.get('statusCode') != '0000':
                raise ValidationError(f"bKash refund failed: {data.get('statusMessage', 'Unknown error')}")
            
            return {
                'success': True,
                'refund_id': data.get('refundID'),
                'transaction_id': data.get('trxID'),
                'amount': float(data.get('amount', refund_amount)),
                'status': data.get('refundStatus', 'Completed')
            }
            
        except requests.RequestException as e:
            logger.error(f"bKash refund network error: {str(e)}")
            raise ValidationError(f"bKash refund failed: Network error - {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"bKash refund response parse error: {str(e)}")
            raise ValidationError(f"bKash refund failed: Invalid response format")
        except Exception as e:
            logger.error(f"bKash refund error: {str(e)}")
            raise ValidationError(f"bKash refund failed: {str(e)}")