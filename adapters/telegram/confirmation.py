"""
Telegram Confirmation Manager - Handles 2-step confirmation for destructive actions.
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class PendingConfirmation:
    """A pending confirmation request."""
    action: str
    params: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    token: str
    details: Dict[str, Any]


class ConfirmationManager:
    """
    Manages 2-step confirmation for critical actions.
    
    Flow:
    1. User clicks destructive action (e.g., "Close Position")
    2. Create confirmation with token
    3. Show confirm dialog with details
    4. User clicks "Confirm" with token
    5. Verify token and execute
    """
    
    TTL_SECONDS = 60  # Confirmations expire after 60 seconds
    
    def __init__(self):
        self.logger = logger.bind(component="confirmation_manager")
        self._pending: Dict[str, PendingConfirmation] = {}
        self._cleanup_interval = 30  # Clean up every 30 seconds
        self._last_cleanup = datetime.now()
    
    def _cleanup_expired(self):
        """Remove expired confirmations."""
        if (datetime.now() - self._last_cleanup).seconds < self._cleanup_interval:
            return
        
        now = datetime.now()
        expired = [k for k, v in self._pending.items() if v.expires_at < now]
        
        for key in expired:
            del self._pending[key]
            self.logger.debug(f"Cleaned up expired confirmation: {key}")
        
        self._last_cleanup = now
    
    def create_confirmation(
        self,
        action: str,
        params: Dict[str, Any],
        details: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a new confirmation request.
        
        Args:
            action: Action type (close, cancel, emergency, etc.)
            params: Original action parameters
            details: Details to show in confirmation dialog
            
        Returns:
            Tuple of (token, confirmation_data)
        """
        self._cleanup_expired()
        
        # Generate unique token
        token = secrets.token_urlsafe(8)[:12]
        
        # Create confirmation
        now = datetime.now()
        confirmation = PendingConfirmation(
            action=action,
            params=params,
            created_at=now,
            expires_at=now + timedelta(seconds=self.TTL_SECONDS),
            token=token,
            details=details
        )
        
        self._pending[token] = confirmation
        
        self.logger.info(f"Created confirmation: action={action} token={token[:6]}...")
        
        return token, {
            'action': action,
            'params': params,
            'details': details,
            'token': token,
            'expires_in': self.TTL_SECONDS
        }
    
    def verify_and_get(self, token: str) -> Optional[PendingConfirmation]:
        """
        Verify token and return confirmation if valid.
        
        Args:
            token: Confirmation token
            
        Returns:
            PendingConfirmation if valid, None if invalid/expired
        """
        self._cleanup_expired()
        
        confirmation = self._pending.get(token)
        
        if not confirmation:
            self.logger.warning(f"Confirmation not found: {token[:6]}...")
            return None
        
        if confirmation.expires_at < datetime.now():
            self.logger.warning(f"Confirmation expired: {token[:6]}...")
            del self._pending[token]
            return None
        
        # Remove after verification (one-time use)
        del self._pending[token]
        
        self.logger.info(f"Confirmation verified: {token[:6]}...")
        
        return confirmation
    
    def request_confirmation(
        self,
        action_type: str,
        symbol: str,
        params: Dict[str, Any],
        user_id: int = None
    ) -> Tuple[str, List[List[Dict[str, str]]]]:
        """
        Request confirmation for an action - returns text and buttons for dialog.
        
        Args:
            action_type: Action type (close, cancel, emergency)
            symbol: Symbol name
            params: Original action parameters
            user_id: User ID
            
        Returns:
            Tuple of (text, buttons)
        """
        short_sym = symbol.replace('-USDT-SWAP', '').replace('/USDT:USDT', '')[:5] if symbol else ''
        
        if action_type == 'close':
            text = f"""⚠️ Pozisyon Kapatma Onayı

📊 {short_sym}

Bu işlem pozisyonunuzu piyasa fiyatından kapatacaktır.

Onaylıyor musunuz?"""
            
            buttons = [
                [
                    {"text": "✅ Onayla", "callback_data": f"ai:act|t=close|s={short_sym}|c=1"},
                    {"text": "❌ İptal", "callback_data": "ai:pos"}
                ]
            ]
        
        elif action_type == 'cancel':
            order_id = params.get('id', '')
            text = f"""⚠️ Emir İptal Onayı

📋 {short_sym} - #{order_id[:8]}...

Bu emir iptal edilecektir.

Onaylıyor musunuz?"""
            
            buttons = [
                [
                    {"text": "✅ Onayla", "callback_data": f"ai:act|t=cancel|id={order_id}|c=1"},
                    {"text": "❌ İptal", "callback_data": "ai:ord"}
                ]
            ]
        
        elif action_type == 'emergency':
            import random
            code = str(random.randint(1000, 9999))
            text = f"""🚨 ACİL DURDURMA

⚠️ Bu işlem:
• TÜM pozisyonları kapatır
• TÜM bekleyen emirleri iptal eder
• Circuit breaker'ı aktive eder

⛔ GERİ ALINAMAZ!

Onaylamak için {code} kodlu butona tıklayın."""
            
            buttons = [
                [
                    {"text": f"🔴 {code} - ONAYLA", "callback_data": f"ai:act|t=emergency|code={code}|c=1"}
                ],
                [
                    {"text": "🔙 İptal", "callback_data": "ai:main"}
                ]
            ]
        
        else:
            text = f"Bilinmeyen işlem: {action_type}"
            buttons = [[{"text": "🔙 Geri", "callback_data": "ai:main"}]]
        
        return text, buttons
    
    def build_close_position_confirm(
        self,
        symbol: str,
        side: str,
        size: float,
        entry: float,
        mark: float,
        upnl: float
    ) -> Tuple[str, List[List[Dict[str, str]]]]:
        """
        Build confirmation dialog for closing a position.
        
        Returns:
            Tuple of (text, buttons)
        """
        upnl_emoji = "📈" if upnl >= 0 else "📉"
        upnl_pct = (upnl / (entry * size) * 100) if entry > 0 and size > 0 else 0
        
        text = f"""⚠️ Confirm Close Position

📊 {symbol}
   Side: {side.upper()}
   Size: {size:.6f}
   Entry: ${entry:,.2f}
   Current: ${mark:,.2f}

{upnl_emoji} Current PnL: ${upnl:,.2f} ({upnl_pct:+.2f}%)

This will close your entire position at market price."""
        
        # Token will be added by caller
        buttons = [
            [
                {"text": "✅ Confirm Close", "callback_data": "ai:act|t=close|s=SYMBOL|c=1"},
                {"text": "❌ Cancel", "callback_data": "ai:pos"}
            ]
        ]
        
        return text, buttons
    
    def build_cancel_order_confirm(
        self,
        order_id: str,
        symbol: str,
        order_type: str,
        side: str,
        price: float,
        size: float
    ) -> Tuple[str, List[List[Dict[str, str]]]]:
        """
        Build confirmation dialog for canceling an order.
        
        Returns:
            Tuple of (text, buttons)
        """
        text = f"""⚠️ Confirm Cancel Order

📋 Order #{order_id[:8]}...
   Symbol: {symbol}
   Type: {order_type.upper()}
   Side: {side.upper()}
   Price: ${price:,.2f}
   Size: {size:.6f}

This order will be cancelled immediately."""
        
        buttons = [
            [
                {"text": "✅ Confirm Cancel", "callback_data": f"ai:act|t=cancel|id={order_id}|c=1"},
                {"text": "❌ Go Back", "callback_data": "ai:ord"}
            ]
        ]
        
        return text, buttons
    
    def build_emergency_confirm(
        self,
        positions_count: int,
        orders_count: int,
        total_exposure: float,
        confirm_code: str
    ) -> Tuple[str, List[List[Dict[str, str]]]]:
        """
        Build confirmation dialog for emergency stop.
        
        Returns:
            Tuple of (text, buttons)
        """
        text = f"""🚨 EMERGENCY STOP

⚠️ This will:
   • Close ALL {positions_count} open positions
   • Cancel ALL {orders_count} pending orders
   • Activate circuit breaker
   • Stop bot from trading

💰 Total Exposure: ${total_exposure:,.2f}

⛔ This action is IRREVERSIBLE!

To confirm, click the button with code: {confirm_code}"""
        
        # Real code button + decoy buttons
        buttons = [
            [
                {"text": f"🔴 {confirm_code} - CONFIRM", "callback_data": f"ai:act|t=emergency|code={confirm_code}"}
            ],
            [
                {"text": "🔙 Cancel - Go Back", "callback_data": "ai:main"}
            ]
        ]
        
        return text, buttons


# Global instance
_confirmation_manager: Optional[ConfirmationManager] = None


def get_confirmation_manager() -> ConfirmationManager:
    """Get the global confirmation manager instance."""
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager
