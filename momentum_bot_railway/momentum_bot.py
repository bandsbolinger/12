"""
MOMENTUM SCALPER V2 - HEADLESS (FOR RAILWAY)
Logs trades and status updates line-by-line.
Optimal for cloud deployment where interactive terminals don't exist.
"""

import websocket
import json
import time
import os
import threading
import sys
from collections import deque
from datetime import datetime

# ================= CONFIG =================
# Override these with environment variables on Railway if needed
SYMBOL = os.getenv("SYMBOL", "SUI_USDT")
WS_URL = "wss://contract.mexc.com/edge"

# Strategy
MOMENTUM_LOOKBACK = 10      # Seconds
MOMENTUM_THRESHOLD = 0.0005 # 0.05%
MAX_HOLD_SECONDS = 15       
TAKE_PROFIT_PCT = 0.003     # 0.3%
STOP_LOSS_PCT = 0.005       # 0.5%
COOLDOWN_SECONDS = 10       

# Risk
ACCOUNT_BALANCE = 100.0
LEVERAGE = 50
RISK_PER_TRADE = 0.10
FEE_RATE = 0.0002           # 0.02% (Standard Taker Fee)

# =========================================

price_history = deque(maxlen=2000) 
current_price = 0.0
balance = ACCOUNT_BALANCE
position = 0.0
entry_price = 0.0
entry_time = 0.0
last_exit_time = 0.0

total_trades = 0
total_wins = 0
realized_pnl = 0.0
peak_balance = ACCOUNT_BALANCE
max_drawdown = 0.0

running = True
last_log_time = 0

def log(msg):
    """Print with timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_momentum():
    if len(price_history) < 2: return 0.0
    target_time = time.time() - MOMENTUM_LOOKBACK
    ref_price = None
    for ts, p in price_history:
        if ts >= target_time:
            ref_price = p
            break
    if ref_price is None or ref_price == 0: return 0.0
    return (current_price - ref_price) / ref_price

def check_logic():
    global position, entry_price, entry_time, last_exit_time
    global balance, realized_pnl, total_trades, total_wins
    global peak_balance, max_drawdown
    
    now = time.time()
    
    # ── EXIT LOGIC ──
    if position != 0:
        hold_time = now - entry_time
        pct_move = ((current_price - entry_price)/entry_price) if position > 0 else ((entry_price - current_price)/entry_price)
        
        should_exit = False
        reason = ""
        
        if pct_move <= -STOP_LOSS_PCT: should_exit = True; reason = "STOP LOSS"
        elif pct_move >= TAKE_PROFIT_PCT: should_exit = True; reason = "TAKE PROFIT"
        elif hold_time >= MAX_HOLD_SECONDS: should_exit = True; reason = "TIME EXIT"
        elif pct_move <= -(1.0 / LEVERAGE): should_exit = True; reason = "LIQUIDATED"
            
        if should_exit:
            pnl = position * (current_price - entry_price)
            fee = abs(position * current_price) * FEE_RATE
            pnl -= fee
            
            balance += pnl
            realized_pnl += pnl
            total_trades += 1
            if pnl > 0: total_wins += 1
            
            peak_balance = max(peak_balance, balance)
            dd = (peak_balance - balance) / peak_balance * 100
            max_drawdown = max(max_drawdown, dd)
            
            side = "LONG" if position > 0 else "SHORT"
            icon = "✅" if pnl > 0 else "❌"
            log(f"{icon} CLOSE {side} | PnL: ${pnl:+.4f} ({reason}) | Hold: {hold_time:.1f}s | Bal: ${balance:.2f}")
            
            position = 0.0
            last_exit_time = now
            return
            
    # ── ENTRY LOGIC ──
    elif now - last_exit_time >= COOLDOWN_SECONDS:
        momentum = get_momentum()
        if abs(momentum) >= MOMENTUM_THRESHOLD:
            size = (balance * LEVERAGE * RISK_PER_TRADE) / current_price
            fee = abs(size * current_price) * FEE_RATE
            
            if momentum > 0: position = size
            else: position = -size
                
            entry_price = current_price
            entry_time = now
            balance -= fee
            
            side = "LONG" if position > 0 else "SHORT"
            log(f"🚀 OPEN {side} @ {entry_price} | Mom: {momentum*100:+.4f}% | Size: ${abs(size*current_price):.2f}")

def status_update():
    """Log periodic status update if nothing is happening"""
    global last_log_time
    now = time.time()
    if now - last_log_time > 60: # Every 60s
        mom = get_momentum() * 100
        pos = "FLAT" if position == 0 else ("LONG" if position > 0 else "SHORT")
        log(f"Running... Price: {current_price} | Mom: {mom:+.4f}% | Pos: {pos} | Bal: ${balance:.2f}")
        last_log_time = now

def on_message(ws, message):
    global current_price
    try:
        data = json.loads(message)
        if "pong" in str(data): return
        
        if data.get("channel") == "push.deal":
            deals = data.get("data", [])
            if deals:
                new_price = float(deals[-1]["p"])
                if new_price != current_price:
                    current_price = new_price
                    price_history.append((time.time(), current_price))
                    check_logic()
                    status_update()
    except Exception: pass

def on_open(ws):
    log(f"Connected to MEXC. Symbol: {SYMBOL}, Leverage: {LEVERAGE}x")
    threading.Thread(target=lambda: ws.send(json.dumps({"method": "sub.deal", "param": {"symbol": SYMBOL}}))).start()
    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

def send_heartbeat(ws):
    while True:
        try:
            ws.send(json.dumps({"method":"ping"}))
            time.sleep(10)
        except: break

def run():
    while running:
        try:
            ws = websocket.WebSocketApp(WS_URL, on_open=on_open, on_message=on_message)
            ws.run_forever()
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    log("Starting Momentum Scalper V2 (Headless)...")
    try:
        run()
    except KeyboardInterrupt:
        log("Stopped.")
