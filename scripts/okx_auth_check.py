import os, sys, time, json
from pathlib import Path

def safe(s):
    if not s: return "(missing)"
    s = s.strip()
    return f"{len(s)} chars, head={s[:3]}..., tail=...{s[-3:]}"

def load_dotenv_if_any():
    # best-effort .env loader
    try:
        from dotenv import load_dotenv
        env = Path(".env")
        if env.exists():
            load_dotenv(dotenv_path=env)
    except Exception:
        pass

def print_env_summary():
    keys = [
        "OKX_API_KEY",
        "OKX_API_SECRET",
        "OKX_API_PASSPHRASE",
        "TELEGRAM_BOT_TOKEN",
        "OKX_SIMULATED",      # "1" means demo key
        "USE_MOCKS",
        "ADAPTERS_OKX_USE_MOCKS",
        "DISABLE_MOCKS"
    ]
    print("=== ENV SUMMARY ===")
    for k in keys:
        v = os.environ.get(k, "")
        if "KEY" in k or "SECRET" in k or "PASSPHRASE" in k or "TOKEN" in k:
            print(f"{k}: {safe(v)}")
        else:
            print(f"{k}: {v!r}")
    print("====================")

def check_okx_auth():
    load_dotenv_if_any()
    print_env_summary()

    try:
        import ccxt
    except Exception as e:
        print("ccxt not installed:", e)
        sys.exit(1)

    apiKey = os.environ.get("OKX_API_KEY", "").strip()
    secret = os.environ.get("OKX_API_SECRET", "").strip()
    password = os.environ.get("OKX_API_PASSPHRASE", "").strip()

    if not (apiKey and secret and password):
        print("❌ Missing OKX credentials")
        sys.exit(2)

    # Try LIVE first
    headers = {}
    simulated_flag = os.environ.get("OKX_SIMULATED", "").strip() in ("1", "true", "True")
    # Only add sim header if we detect it's needed
    def make_ex(sim=False):
        opts = {
            "apiKey": apiKey,
            "secret": secret,
            "password": password,
            "timeout": 15000,
            "enableRateLimit": True,
            "headers": {"x-simulated-trading": "1"} if sim else {},
            "options": {},  # leave defaults
        }
        return ccxt.okx(opts)

    def try_fetch_balance(ex):
        try:
            # private endpoint
            bal = ex.fetch_balance()
            print("✅ fetch_balance OK:", json.dumps(list(bal.keys())[:5]))
            return True, ""
        except Exception as e:
            return False, str(e)

    print("→ Trying LIVE (no simulated header)...")
    live_ok, live_err = try_fetch_balance(make_ex(sim=False))
    if live_ok:
        print("✅ LIVE auth succeeded.")
        return 0

    print("LIVE failed:", live_err)

    # Heuristic: if error mentions invalid key, try SIM header
    hint = live_err.lower()
    if "invalid ok-access-key" in hint or "api key" in hint or "not found" in hint:
        print("→ Trying SIMULATED header (x-simulated-trading: 1)...")
        sim_ok, sim_err = try_fetch_balance(make_ex(sim=True))
        if sim_ok:
            print("✅ SIMULATED auth succeeded. Your key is likely a DEMO key.")
            print("Set OKX_SIMULATED=1 in .env to always send the simulated header in runtime.")
            return 0
        else:
            print("❌ SIMULATED also failed:", sim_err)

    # If we're here, both paths failed
    print("❌ Auth failed. Check:")
    print("1) OKX API key active + Read/Trade perms")
    print("2) Correct Passphrase")
    print("3) IP restrictions allow your machine")
    print("4) DEMO vs LIVE key mismatch (use simulated header for DEMO)")
    return 3

if __name__ == "__main__":
    sys.exit(check_okx_auth())
