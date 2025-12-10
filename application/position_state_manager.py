"""
Position State Manager - SOLID Compliant State Machine
Manages position states and transitions according to trading policy.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple
from loguru import logger


class PositionState(Enum):
    """Position states for state machine."""
    READY = "READY"                    # No open position
    LONG_OPEN = "LONG_OPEN"           # Long position open
    SHORT_OPEN = "SHORT_OPEN"         # Short position open
    COOLDOWN = "COOLDOWN"             # Post-closure cooldown period


@dataclass
class PositionInfo:
    """Position information for state tracking."""
    symbol: str
    state: PositionState
    entry_time: datetime
    entry_price: float
    size: float
    side: str  # 'long' or 'short'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    holding_bars: int = 0
    r_multiple: float = 0.0
    consecutive_losses: int = 0
    cooldown_until: Optional[datetime] = None


@dataclass
class StateTransition:
    """State transition result."""
    from_state: PositionState
    to_state: PositionState
    action: str  # 'IGNORE', 'OPEN_LONG', 'OPEN_SHORT', 'CLOSE', 'REVERSE', 'COOLDOWN'
    reason: str
    timestamp: datetime


class StateTransitionRule(ABC):
    """Abstract base for state transition rules."""
    
    @abstractmethod
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        """Check if transition is allowed."""
        pass
    
    @abstractmethod
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        """Get the transition details."""
        pass


class ReadyToOpenRule(StateTransitionRule):
    """Rule for READY -> LONG_OPEN/SHORT_OPEN transitions."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
    
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        if current_state != PositionState.READY:
            return False
        
        # Check gating first - must be valid (Gate=PASS)
        is_valid = signal.get('is_valid', False) if isinstance(signal, dict) else getattr(signal, 'is_valid', False)
        if not is_valid:
            return False
        
        # Check direction - must be long or short, not flat
        direction = signal.get('direction', 'flat') if isinstance(signal, dict) else getattr(signal, 'direction', 'flat')
        if direction == 'flat':
            return False
        
        # NOTE: size and mode checks removed - these are execution-time concerns, not gating
        # Size is calculated during execution, mode is checked in execution pipeline
        
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        return final_score >= enter_long or final_score <= enter_short
    
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        if final_score >= enter_long:
            return StateTransition(
                from_state=PositionState.READY,
                to_state=PositionState.LONG_OPEN,
                action='OPEN_LONG',
                reason=f'Long signal: score={final_score:.1f} >= {enter_long}',
                timestamp=datetime.now()
            )
        else:
            return StateTransition(
                from_state=PositionState.READY,
                to_state=PositionState.SHORT_OPEN,
                action='OPEN_SHORT',
                reason=f'Short signal: score={final_score:.1f} <= {enter_short}',
                timestamp=datetime.now()
            )


class SameDirectionIgnoreRule(StateTransitionRule):
    """Rule for ignoring same direction signals."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
    
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        if current_state not in [PositionState.LONG_OPEN, PositionState.SHORT_OPEN]:
            return False
        
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        enter_long = self.policy['trading']['scoring']['decision_thresholds']['enter_long']
        enter_short = self.policy['trading']['scoring']['decision_thresholds']['enter_short']
        
        # Same direction signal
        if current_state == PositionState.LONG_OPEN and final_score >= enter_long:
            return True
        elif current_state == PositionState.SHORT_OPEN and final_score <= enter_short:
            return True
        
        return False
    
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        return StateTransition(
            from_state=current_state,
            to_state=current_state,
            action='IGNORE',
            reason=f'Same direction signal ignored',
            timestamp=datetime.now()
        )


class ReversalRule(StateTransitionRule):
    """Rule for reversal transitions (LONG_OPEN -> SHORT_OPEN, SHORT_OPEN -> LONG_OPEN)."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
    
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        if current_state not in [PositionState.LONG_OPEN, PositionState.SHORT_OPEN]:
            return False
        
        if not position_info:
            return False
        
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        exit_long = self.policy['trading']['scoring']['decision_thresholds']['exit_long']
        exit_short = self.policy['trading']['scoring']['decision_thresholds']['exit_short']
        min_hold_bars = self.policy['trading']['scoring']['position_management']['min_hold_bars']
        
        # Check if opposite signal and min holding period met
        if current_state == PositionState.LONG_OPEN:
            return final_score <= exit_long and position_info.holding_bars >= min_hold_bars
        else:  # SHORT_OPEN
            return final_score >= exit_short and position_info.holding_bars >= min_hold_bars
    
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        final_score = signal.get('final_score', 0) if isinstance(signal, dict) else getattr(signal, 'final_score', 0)
        
        if current_state == PositionState.LONG_OPEN:
            return StateTransition(
                from_state=PositionState.LONG_OPEN,
                to_state=PositionState.SHORT_OPEN,
                action='REVERSE',
                reason=f'Long to Short reversal: score={final_score:.1f}',
                timestamp=datetime.now()
            )
        else:
            return StateTransition(
                from_state=PositionState.SHORT_OPEN,
                to_state=PositionState.LONG_OPEN,
                action='REVERSE',
                reason=f'Short to Long reversal: score={final_score:.1f}',
                timestamp=datetime.now()
            )


class CooldownRule(StateTransitionRule):
    """Rule for transitions to COOLDOWN state."""
    
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        # This rule is triggered by external events (TP/SL hit, manual close)
        return False  # Handled by external triggers
    
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        return StateTransition(
            from_state=current_state,
            to_state=PositionState.COOLDOWN,
            action='COOLDOWN',
            reason='Position closed (TP/SL/Manual)',
            timestamp=datetime.now()
        )


class CooldownToReadyRule(StateTransitionRule):
    """Rule for COOLDOWN -> READY transitions."""
    
    def can_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> bool:
        if current_state != PositionState.COOLDOWN:
            return False
        
        if not position_info or not position_info.cooldown_until:
            return True  # No cooldown set, can transition
        
        return datetime.now() >= position_info.cooldown_until
    
    def get_transition(self, current_state: PositionState, signal: Dict, position_info: Optional[PositionInfo]) -> StateTransition:
        return StateTransition(
            from_state=PositionState.COOLDOWN,
            to_state=PositionState.READY,
            action='READY',
            reason='Cooldown period expired',
            timestamp=datetime.now()
        )


class PositionStateManager:
    """Main position state manager with SOLID principles."""
    
    def __init__(self, policy: Dict):
        self.policy = policy
        self.positions: Dict[str, PositionInfo] = {}
        self.transition_history: Dict[str, list] = {}
        
        # Initialize transition rules
        self.rules = [
            ReadyToOpenRule(policy),
            SameDirectionIgnoreRule(policy),
            ReversalRule(policy),
            CooldownRule(),
            CooldownToReadyRule()
        ]
        
        logger.info("PositionStateManager initialized with policy-based rules")
    
    def get_position_state(self, symbol: str) -> PositionState:
        """Get current position state for symbol."""
        if symbol not in self.positions:
            return PositionState.READY
        
        position = self.positions[symbol]
        
        # Check if cooldown expired
        if position.state == PositionState.COOLDOWN and position.cooldown_until:
            if datetime.now() >= position.cooldown_until:
                self._transition_to_ready(symbol)
                return PositionState.READY
        
        return position.state
    
    def process_signal(self, symbol: str, signal: Dict) -> StateTransition:
        """Process signal and return state transition."""
        current_state = self.get_position_state(symbol)
        position_info = self.positions.get(symbol)
        
        # Find applicable rule
        for rule in self.rules:
            if rule.can_transition(current_state, signal, position_info):
                transition = rule.get_transition(current_state, signal, position_info)
                self._apply_transition(symbol, transition)
                return transition
        
        # No applicable rule - maintain current state
        return StateTransition(
            from_state=current_state,
            to_state=current_state,
            action='MAINTAIN',
            reason='No applicable transition rule',
            timestamp=datetime.now()
        )
    
    def open_position(self, symbol: str, side: str, entry_price: float, size: float, 
                     stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> bool:
        """Open a new position."""
        if self.get_position_state(symbol) != PositionState.READY:
            logger.warning(f"[ENTRY] Cannot open position for {symbol}: not in READY state")
            return False
        
        state = PositionState.LONG_OPEN if side.lower() == 'long' else PositionState.SHORT_OPEN
        
        self.positions[symbol] = PositionInfo(
            symbol=symbol,
            state=state,
            entry_time=datetime.now(),
            entry_price=entry_price,
            size=size,
            side=side.lower(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            holding_bars=0,
            r_multiple=0.0,
            consecutive_losses=0
        )
        
        logger.info(f"[ENTRY] {side.upper()} position opened for {symbol} @ {entry_price}")
        return True
    
    def close_position(self, symbol: str, reason: str = "Manual") -> bool:
        """Close position and enter cooldown."""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        old_state = position.state
        
        # Calculate cooldown duration
        cooldown_bars = self._calculate_cooldown_bars(position)
        cooldown_seconds = cooldown_bars * 15 * 60  # 15 minutes per bar
        cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
        
        # Update position to cooldown
        position.state = PositionState.COOLDOWN
        position.cooldown_until = cooldown_until
        
        logger.info(f"[CLOSE] {old_state.value} position closed for {symbol} reason={reason}")
        logger.info(f"[COOLDOWN] {cooldown_bars} bars until {cooldown_until.strftime('%H:%M:%S')}")
        
        return True
    
    def update_position_metrics(self, symbol: str, current_price: float, holding_bars: int):
        """Update position metrics (R-multiple, holding bars)."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        position.holding_bars = holding_bars
        
        # Calculate R-multiple
        if position.side == 'long':
            position.r_multiple = (current_price - position.entry_price) / position.entry_price
        else:
            position.r_multiple = (position.entry_price - current_price) / position.entry_price
    
    def _apply_transition(self, symbol: str, transition: StateTransition):
        """Apply state transition."""
        if symbol not in self.transition_history:
            self.transition_history[symbol] = []
        
        self.transition_history[symbol].append(transition)
        
        # Update position state
        if symbol in self.positions:
            self.positions[symbol].state = transition.to_state
        
        logger.info(f"[STATE] {symbol}: {transition.from_state.value} -> {transition.to_state.value} "
                   f"action={transition.action} reason={transition.reason}")
    
    def _transition_to_ready(self, symbol: str):
        """Transition symbol to READY state."""
        if symbol in self.positions:
            self.positions[symbol].state = PositionState.READY
            self.positions[symbol].cooldown_until = None
    
    def _calculate_cooldown_bars(self, position: PositionInfo) -> int:
        """Calculate cooldown duration based on consecutive losses."""
        base_bars = self.policy['trading']['scoring']['position_management']['cooldown']['base_bars']
        max_bars = self.policy['trading']['scoring']['position_management']['cooldown']['max_bars']
        loss_multiplier = self.policy['trading']['scoring']['position_management']['cooldown']['loss_multiplier']
        
        cooldown_bars = base_bars * (1 + position.consecutive_losses * loss_multiplier)
        return min(int(cooldown_bars), max_bars)
    
    def get_position_info(self, symbol: str) -> Optional[PositionInfo]:
        """Get position information."""
        return self.positions.get(symbol)
    
    def is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown."""
        return self.get_position_state(symbol) == PositionState.COOLDOWN
    
    def get_cooldown_remaining(self, symbol: str) -> Optional[timedelta]:
        """Get remaining cooldown time."""
        position = self.positions.get(symbol)
        if not position or not position.cooldown_until:
            return None
        
        remaining = position.cooldown_until - datetime.now()
        return remaining if remaining.total_seconds() > 0 else None
