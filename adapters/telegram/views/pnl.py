"""
PnL View Builder - Interactive PnL tracking with multiple views.

Features:
- Main PnL summary (today, week, month, all-time)
- Per-coin analysis with top gainers/losers
- Detailed coin view with trade history
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from adapters.telegram.formatter import TelegramFormatter, get_formatter


def build_pnl_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build main PnL view with summary and navigation."""
    if formatter is None:
        formatter = get_formatter()
    
    report = context.get('pnl_report', {})
    error = report.get('error')
    
    if error:
        lines = [
            "📊 <b>PNL REPORT</b>",
            "",
            f"❌ Error: {error}",
            "",
            "Check OKX connection."
        ]
        buttons = [[{"text": "🔄 Refresh", "callback_data": "ai:pnl"}, {"text": "🏠 Home", "callback_data": "ai:main"}]]
        return "\n".join(lines), buttons
    
    # Get summaries
    today = report.get('today', {})
    week = report.get('week', {})
    month = report.get('month', {})
    all_time = report.get('all_time', {})
    
    # Get balance info from context
    balance = context.get('balance', 0)
    unrealized_pnl = context.get('unrealized_pnl', 0)
    
    lines = [
        "📊 <b>PNL REPORT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"💼 Balance: <b>${balance:,.2f}</b>",
        f"📈 Open Position: ${unrealized_pnl:+,.2f}",
        "",
        "━━━━ Profit/Loss Summary ━━━━",
        "",
    ]
    
    # Today
    pnl_today = today.get('total_pnl', 0)
    trades_today = today.get('total_trades', 0)
    wr_today = today.get('win_rate', 0)
    emoji_today = "🟢" if pnl_today >= 0 else "🔴"
    lines.append(f"{emoji_today} <b>Today:</b> ${pnl_today:+,.2f} ({trades_today} trades, {wr_today:.0f}%)")
    
    # Week
    pnl_week = week.get('total_pnl', 0)
    trades_week = week.get('total_trades', 0)
    wr_week = week.get('win_rate', 0)
    emoji_week = "🟢" if pnl_week >= 0 else "🔴"
    lines.append(f"{emoji_week} <b>This Week:</b> ${pnl_week:+,.2f} ({trades_week} trades, {wr_week:.0f}%)")
    
    # Month
    pnl_month = month.get('total_pnl', 0)
    trades_month = month.get('total_trades', 0)
    wr_month = month.get('win_rate', 0)
    emoji_month = "🟢" if pnl_month >= 0 else "🔴"
    lines.append(f"{emoji_month} <b>This Month:</b> ${pnl_month:+,.2f} ({trades_month} trades, {wr_month:.0f}%)")
    
    # All-time
    pnl_all = all_time.get('total_pnl', 0)
    trades_all = all_time.get('total_trades', 0)
    fees_all = all_time.get('fees_paid', 0)
    emoji_all = "💎" if pnl_all >= 0 else "💸"
    lines.append(f"{emoji_all} <b>Total:</b> ${pnl_all:+,.2f} ({trades_all} trades)")
    
    # Fees
    lines.append(f"💰 <i>Fees Paid:</i> ${fees_all:.2f}")
    
    lines.append("")
    lines.append("━━━━ Top Gainers/Losers ━━━━")
    
    # Top gainers
    top_gainers = report.get('top_gainers', [])
    if top_gainers:
        lines.append("")
        lines.append("🏆 <b>Top Gainers:</b>")
        for i, (coin, pnl) in enumerate(top_gainers[:3]):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "•"
            lines.append(f"{medal} {coin}: ${pnl:+,.2f}")
    
    # Top losers
    top_losers = report.get('top_losers', [])
    if top_losers and top_losers[0][1] < 0:
        lines.append("")
        lines.append("📉 <b>Top Losers:</b>")
        for coin, pnl in top_losers[:3]:
            if pnl < 0:
                lines.append(f"• {coin}: ${pnl:,.2f}")
    
    # Timestamp
    updated = report.get('updated_at', '')
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            lines.append("")
            lines.append(f"⏰ {dt.strftime('%H:%M:%S')}")
        except:
            pass
    
    text = "\n".join(lines)
    
    # Buttons
    buttons = [
        [
            {"text": "🔄 Refresh", "callback_data": "ai:pnl"},
            {"text": "🪙 By Coin", "callback_data": "ai:pnl_coins"},
        ],
        [
            {"text": "📅 Today", "callback_data": "ai:pnl_day"},
            {"text": "📆 Week", "callback_data": "ai:pnl_week"},
            {"text": "📆 Month", "callback_data": "ai:pnl_month"},
        ],
        [
            {"text": "🏠 Home", "callback_data": "ai:main"},
            {"text": "📊 Positions", "callback_data": "ai:pos"},
        ]
    ]
    
    return text, buttons


def build_pnl_coins_view(context: Dict[str, Any], formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build per-coin PnL breakdown view."""
    if formatter is None:
        formatter = get_formatter()
    
    report = context.get('pnl_report', {})
    per_coin = report.get('per_coin', {})
    
    lines = [
        "🪙 <b>PnL By Coin</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    if not per_coin:
        lines.append("📭 No trades yet")
    else:
        # Sort by PnL
        sorted_coins = sorted(per_coin.items(), key=lambda x: x[1]['pnl'], reverse=True)
        
        for coin, data in sorted_coins[:12]:  # Max 12 coins
            pnl = data['pnl']
            trades = data['trades']
            wr = data['win_rate']
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            sign = "+" if pnl >= 0 else ""
            
            lines.append(f"{emoji} <b>{coin}</b>: {sign}${pnl:.2f} ({trades} tr, %{wr:.0f})")
    
    # Timestamp
    updated = report.get('updated_at', '')
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            lines.append("")
            lines.append(f"⏰ {dt.strftime('%H:%M:%S')}")
        except:
            pass
    
    text = "\n".join(lines)
    
    buttons = [
        [
            {"text": "🔄 Refresh", "callback_data": "ai:pnl_coins"},
            {"text": "📊 Summary", "callback_data": "ai:pnl"},
        ],
        [
            {"text": "🏠 Home", "callback_data": "ai:main"},
        ]
    ]
    
    return text, buttons


def build_pnl_period_view(context: Dict[str, Any], period: str, formatter: TelegramFormatter = None) -> Tuple[str, List[List[Dict[str, str]]]]:
    """Build PnL view for a specific time period with per-coin analysis."""
    if formatter is None:
        formatter = get_formatter()
    
    report = context.get('pnl_report', {})
    
    period_names = {'day': 'Today', 'week': 'This Week', 'month': 'This Month'}
    period_keys = {'day': 'today', 'week': 'week', 'month': 'month'}
    
    period_name = period_names.get(period, period)
    period_key = period_keys.get(period, 'today')
    data = report.get(period_key, {})
    
    pnl = data.get('total_pnl', 0)
    trades = data.get('total_trades', 0)
    wins = data.get('wins', 0)
    losses = data.get('losses', 0)
    wr = data.get('win_rate', 0)
    avg_win = data.get('avg_win', 0)
    avg_loss = data.get('avg_loss', 0)
    best = data.get('best_trade', 0)
    worst = data.get('worst_trade', 0)
    fees = data.get('fees_paid', 0)
    
    emoji = "🟢" if pnl >= 0 else "🔴"
    
    lines = [
        f"📅 <b>{period_name} Details</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{emoji} <b>Total PnL:</b> ${pnl:+,.2f}",
        "",
        f"📊 Trades: {trades} | ✅ {wins} | ❌ {losses}",
        f"📈 Win Rate: {wr:.0f}%",
        "",
        f"💰 Avg Win: ${avg_win:+,.2f}",
        f"💸 Avg Loss: ${avg_loss:,.2f}",
        f"💳 Fees: ${fees:.2f}",
    ]
    
    # Add per-period top gainers/losers
    gainers_key = f'top_gainers_{period_key}'
    losers_key = f'top_losers_{period_key}'
    
    top_gainers = report.get(gainers_key, [])
    top_losers = report.get(losers_key, [])
    
    if top_gainers:
        lines.append("")
        lines.append("🏆 <b>Top Gainers:</b>")
        for coin, pnl_val in top_gainers[:3]:
            if pnl_val > 0:
                lines.append(f"   🟢 {coin}: ${pnl_val:+,.2f}")
    
    if top_losers:
        has_losers = any(pnl_val < 0 for _, pnl_val in top_losers[:3])
        if has_losers:
            lines.append("")
            lines.append("📉 <b>Top Losers:</b>")
            for coin, pnl_val in top_losers[:3]:
                if pnl_val < 0:
                    lines.append(f"   🔴 {coin}: ${pnl_val:,.2f}")
    
    text = "\n".join(lines)
    
    buttons = [
        [
            {"text": "📅 Today", "callback_data": "ai:pnl_day"},
            {"text": "📆 Week", "callback_data": "ai:pnl_week"},
            {"text": "📆 Month", "callback_data": "ai:pnl_month"},
        ],
        [
            {"text": "🪙 By Coin", "callback_data": "ai:pnl_coins"},
            {"text": "📊 Summary", "callback_data": "ai:pnl"},
        ],
        [
            {"text": "🏠 Home", "callback_data": "ai:main"},
        ]
    ]
    
    return text, buttons
