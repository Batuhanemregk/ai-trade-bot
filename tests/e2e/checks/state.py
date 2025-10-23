"""
State Machine Checker
===================

State machine kontrolleri:
- Position state transitions (READY→ENTER_PENDING→HOLDING→EXITING)
- State transition rules validation
- Cooldown period management
- State consistency checks
- Transition history tracking
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class PositionState(Enum):
    """Position states for state machine."""
    READY = "READY"                    # No open position
    ENTER_PENDING = "ENTER_PENDING"    # Entry order placed
    HOLDING = "HOLDING"                # Position open
    EXITING = "EXITING"                # Exit order placed
    COOLDOWN = "COOLDOWN"              # Post-closure cooldown period


@dataclass
class StateTransition:
    """State transition event."""
    timestamp: datetime
    symbol: str
    from_state: PositionState
    to_state: PositionState
    trigger: str  # signal, order_fill, timeout, manual
    reason: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class PositionInfo:
    """Position information for state tracking."""
    symbol: str
    state: PositionState
    entry_time: Optional[datetime] = None
    entry_price: float = 0.0
    size: float = 0.0
    side: str = ""  # long, short
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    holding_bars: int = 0
    r_multiple: float = 0.0
    consecutive_losses: int = 0
    cooldown_until: Optional[datetime] = None


class StateMachineChecker:
    """Checks state machine transitions and consistency."""
    
    def __init__(self):
        self.positions: Dict[str, PositionInfo] = {}
        self.transitions: List[StateTransition] = []
        self.transition_rules = self._init_transition_rules()
        
    def _init_transition_rules(self) -> Dict[Tuple[PositionState, PositionState], bool]:
        """Initialize valid transition rules."""
        return {
            # From READY
            (PositionState.READY, PositionState.ENTER_PENDING): True,
            (PositionState.READY, PositionState.READY): True,  # Stay in READY
            
            # From ENTER_PENDING
            (PositionState.ENTER_PENDING, PositionState.HOLDING): True,
            (PositionState.ENTER_PENDING, PositionState.READY): True,  # Order cancelled
            
            # From HOLDING
            (PositionState.HOLDING, PositionState.EXITING): True,
            (PositionState.HOLDING, PositionState.HOLDING): True,  # Stay in HOLDING
            
            # From EXITING
            (PositionState.EXITING, PositionState.COOLDOWN): True,
            (PositionState.EXITING, PositionState.HOLDING): True,  # Exit cancelled
            
            # From COOLDOWN
            (PositionState.COOLDOWN, PositionState.READY): True,
            (PositionState.COOLDOWN, PositionState.COOLDOWN): True,  # Stay in COOLDOWN
        }
    
    async def check_state_transition(self, symbol: str, from_state: PositionState, 
                                   to_state: PositionState, trigger: str, 
                                   reason: str) -> Tuple[bool, str]:
        """
        Check if state transition is valid.
        
        Args:
            symbol: Trading symbol
            from_state: Current state
            to_state: Target state
            trigger: What triggered the transition
            reason: Reason for transition
            
        Returns:
            (success, message)
        """
        try:
            # Check if transition is allowed
            transition_key = (from_state, to_state)
            if not self.transition_rules.get(transition_key, False):
                return False, f"Invalid transition: {from_state.value} → {to_state.value}"
            
            # Record transition
            transition = StateTransition(
                timestamp=datetime.now(),
                symbol=symbol,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                reason=reason
            )
            self.transitions.append(transition)
            
            # Update position state
            if symbol not in self.positions:
                self.positions[symbol] = PositionInfo(symbol=symbol, state=from_state)
            
            self.positions[symbol].state = to_state
            
            logger.info(f"✅ State transition: {symbol} {from_state.value} → {to_state.value} ({trigger})")
            return True, f"State transition: {from_state.value} → {to_state.value}"
            
        except Exception as e:
            logger.error(f"❌ State transition check failed: {e}")
            return False, f"State transition check failed: {e}"
    
    async def check_ready_to_enter_pending(self, symbol: str, signal: Dict) -> Tuple[bool, str]:
        """
        Check READY → ENTER_PENDING transition.
        
        Args:
            symbol: Trading symbol
            signal: Trading signal
            
        Returns:
            (success, message)
        """
        try:
            # Check if symbol is in READY state
            if symbol not in self.positions:
                self.positions[symbol] = PositionInfo(symbol=symbol, state=PositionState.READY)
            
            current_state = self.positions[symbol].state
            
            if current_state != PositionState.READY:
                return False, f"Not in READY state: {current_state.value}"
            
            # Check if signal is valid
            if not signal.get('is_valid', False):
                return False, "Signal not valid"
            
            # Check signal direction
            direction = signal.get('direction', '').lower()
            if direction not in ['long', 'short']:
                return False, f"Invalid signal direction: {direction}"
            
            # Transition to ENTER_PENDING
            success, message = await self.check_state_transition(
                symbol, PositionState.READY, PositionState.ENTER_PENDING,
                "signal", f"Valid {direction} signal"
            )
            
            if success:
                # Update position info
                self.positions[symbol].side = direction
                self.positions[symbol].entry_time = datetime.now()
                
            return success, message
            
        except Exception as e:
            logger.error(f"❌ READY → ENTER_PENDING check failed: {e}")
            return False, f"READY → ENTER_PENDING check failed: {e}"
    
    async def check_enter_pending_to_holding(self, symbol: str, order_filled: bool) -> Tuple[bool, str]:
        """
        Check ENTER_PENDING → HOLDING transition.
        
        Args:
            symbol: Trading symbol
            order_filled: Whether entry order was filled
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not found"
            
            current_state = self.positions[symbol].state
            
            if current_state != PositionState.ENTER_PENDING:
                return False, f"Not in ENTER_PENDING state: {current_state.value}"
            
            if not order_filled:
                return False, "Entry order not filled"
            
            # Transition to HOLDING
            success, message = await self.check_state_transition(
                symbol, PositionState.ENTER_PENDING, PositionState.HOLDING,
                "order_fill", "Entry order filled"
            )
            
            if success:
                # Update position info
                self.positions[symbol].holding_bars = 0
                
            return success, message
            
        except Exception as e:
            logger.error(f"❌ ENTER_PENDING → HOLDING check failed: {e}")
            return False, f"ENTER_PENDING → HOLDING check failed: {e}"
    
    async def check_holding_to_exiting(self, symbol: str, exit_signal: Dict) -> Tuple[bool, str]:
        """
        Check HOLDING → EXITING transition.
        
        Args:
            symbol: Trading symbol
            exit_signal: Exit signal
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not found"
            
            current_state = self.positions[symbol].state
            
            if current_state != PositionState.HOLDING:
                return False, f"Not in HOLDING state: {current_state.value}"
            
            # Check if exit signal is valid
            if not exit_signal.get('is_valid', False):
                return False, "Exit signal not valid"
            
            # Check minimum holding time
            if self.positions[symbol].holding_bars < 3:  # Min 3 bars
                return False, f"Minimum holding time not met: {self.positions[symbol].holding_bars} bars"
            
            # Transition to EXITING
            success, message = await self.check_state_transition(
                symbol, PositionState.HOLDING, PositionState.EXITING,
                "exit_signal", f"Valid exit signal: {exit_signal.get('direction', 'unknown')}"
            )
            
            return success, message
            
        except Exception as e:
            logger.error(f"❌ HOLDING → EXITING check failed: {e}")
            return False, f"HOLDING → EXITING check failed: {e}"
    
    async def check_exiting_to_cooldown(self, symbol: str, position_closed: bool) -> Tuple[bool, str]:
        """
        Check EXITING → COOLDOWN transition.
        
        Args:
            symbol: Trading symbol
            position_closed: Whether position was closed
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not found"
            
            current_state = self.positions[symbol].state
            
            if current_state != PositionState.EXITING:
                return False, f"Not in EXITING state: {current_state.value}"
            
            if not position_closed:
                return False, "Position not closed"
            
            # Transition to COOLDOWN
            success, message = await self.check_state_transition(
                symbol, PositionState.EXITING, PositionState.COOLDOWN,
                "position_closed", "Position closed"
            )
            
            if success:
                # Set cooldown period
                cooldown_duration = timedelta(minutes=30)  # 30 minutes cooldown
                self.positions[symbol].cooldown_until = datetime.now() + cooldown_duration
                
            return success, message
            
        except Exception as e:
            logger.error(f"❌ EXITING → COOLDOWN check failed: {e}")
            return False, f"EXITING → COOLDOWN check failed: {e}"
    
    async def check_cooldown_to_ready(self, symbol: str) -> Tuple[bool, str]:
        """
        Check COOLDOWN → READY transition.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not found"
            
            current_state = self.positions[symbol].state
            
            if current_state != PositionState.COOLDOWN:
                return False, f"Not in COOLDOWN state: {current_state.value}"
            
            # Check if cooldown period has expired
            if self.positions[symbol].cooldown_until and datetime.now() < self.positions[symbol].cooldown_until:
                remaining = self.positions[symbol].cooldown_until - datetime.now()
                return False, f"Cooldown not expired: {remaining.total_seconds():.0f}s remaining"
            
            # Transition to READY
            success, message = await self.check_state_transition(
                symbol, PositionState.COOLDOWN, PositionState.READY,
                "cooldown_expired", "Cooldown period expired"
            )
            
            if success:
                # Reset position info
                self.positions[symbol] = PositionInfo(symbol=symbol, state=PositionState.READY)
                
            return success, message
            
        except Exception as e:
            logger.error(f"❌ COOLDOWN → READY check failed: {e}")
            return False, f"COOLDOWN → READY check failed: {e}"
    
    async def check_state_consistency(self, symbol: str, actual_position: Dict) -> Tuple[bool, str]:
        """
        Check state consistency with actual position.
        
        Args:
            symbol: Trading symbol
            actual_position: Actual position from exchange
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not tracked in state machine"
            
            tracked_state = self.positions[symbol].state
            actual_size = float(actual_position.get('size', 0))
            
            # Check consistency
            if actual_size == 0 and tracked_state in [PositionState.HOLDING, PositionState.EXITING]:
                return False, f"State inconsistency: tracked={tracked_state.value}, actual=no_position"
            elif actual_size != 0 and tracked_state == PositionState.READY:
                return False, f"State inconsistency: tracked={tracked_state.value}, actual=has_position"
            
            logger.info(f"✅ State consistency: {symbol} {tracked_state.value} matches actual position")
            return True, f"State consistent: {tracked_state.value}"
            
        except Exception as e:
            logger.error(f"❌ State consistency check failed: {e}")
            return False, f"State consistency check failed: {e}"
    
    async def check_cooldown_management(self, symbol: str) -> Tuple[bool, str]:
        """
        Check cooldown period management.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (success, message)
        """
        try:
            if symbol not in self.positions:
                return False, "Position not found"
            
            position = self.positions[symbol]
            
            if position.state != PositionState.COOLDOWN:
                return True, f"Not in cooldown: {position.state.value}"
            
            if not position.cooldown_until:
                return False, "Cooldown period not set"
            
            remaining = position.cooldown_until - datetime.now()
            
            if remaining.total_seconds() <= 0:
                # Cooldown expired, should transition to READY
                success, message = await self.check_cooldown_to_ready(symbol)
                return success, message
            else:
                logger.info(f"✅ Cooldown active: {symbol} {remaining.total_seconds():.0f}s remaining")
                return True, f"Cooldown active: {remaining.total_seconds():.0f}s remaining"
                
        except Exception as e:
            logger.error(f"❌ Cooldown management check failed: {e}")
            return False, f"Cooldown management check failed: {e}"
    
    async def check_transition_history(self, symbol: str) -> Tuple[bool, str]:
        """
        Check transition history for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (success, message)
        """
        try:
            symbol_transitions = [t for t in self.transitions if t.symbol == symbol]
            
            if not symbol_transitions:
                return True, "No transitions recorded"
            
            # Check for invalid transitions
            invalid_transitions = []
            for transition in symbol_transitions:
                transition_key = (transition.from_state, transition.to_state)
                if not self.transition_rules.get(transition_key, False):
                    invalid_transitions.append(f"{transition.from_state.value} → {transition.to_state.value}")
            
            if invalid_transitions:
                return False, f"Invalid transitions found: {invalid_transitions}"
            
            # Check transition sequence
            if len(symbol_transitions) > 1:
                # Sort by timestamp
                symbol_transitions.sort(key=lambda t: t.timestamp)
                
                # Check if transitions follow logical sequence
                for i in range(1, len(symbol_transitions)):
                    prev_transition = symbol_transitions[i-1]
                    curr_transition = symbol_transitions[i]
                    
                    if prev_transition.to_state != curr_transition.from_state:
                        return False, f"Transition sequence broken: {prev_transition.to_state.value} ≠ {curr_transition.from_state.value}"
            
            logger.info(f"✅ Transition history valid: {symbol} {len(symbol_transitions)} transitions")
            return True, f"Transition history valid: {len(symbol_transitions)} transitions"
            
        except Exception as e:
            logger.error(f"❌ Transition history check failed: {e}")
            return False, f"Transition history check failed: {e}"
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of all states."""
        return {
            'total_positions': len(self.positions),
            'total_transitions': len(self.transitions),
            'positions_by_state': {
                state.value: len([p for p in self.positions.values() if p.state == state])
                for state in PositionState
            },
            'transitions_by_trigger': {
                trigger: len([t for t in self.transitions if t.trigger == trigger])
                for trigger in set(t.trigger for t in self.transitions)
            },
            'active_cooldowns': len([p for p in self.positions.values() if p.state == PositionState.COOLDOWN])
        }
    
    def get_transition_history(self) -> List[Dict]:
        """Get all transitions for analysis."""
        return [
            {
                'timestamp': t.timestamp.isoformat(),
                'symbol': t.symbol,
                'from_state': t.from_state.value,
                'to_state': t.to_state.value,
                'trigger': t.trigger,
                'reason': t.reason,
                'details': t.details
            }
            for t in self.transitions
        ]
    
    def get_position_states(self) -> List[Dict]:
        """Get all position states for analysis."""
        return [
            {
                'symbol': p.symbol,
                'state': p.state.value,
                'entry_time': p.entry_time.isoformat() if p.entry_time else None,
                'entry_price': p.entry_price,
                'size': p.size,
                'side': p.side,
                'holding_bars': p.holding_bars,
                'cooldown_until': p.cooldown_until.isoformat() if p.cooldown_until else None
            }
            for p in self.positions.values()
        ]

