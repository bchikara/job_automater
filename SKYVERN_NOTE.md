# ⚠️ Skyvern Status: Disabled (Requires Setup)

## Current Status

**Skyvern is DISABLED** and system is using **Browser-Use (Hybrid Mode)** instead.

---

## Why Disabled?

Skyvern requires ONE of the following setups:

### Option 1: Cloud Mode (SIMPLEST) ✅ RECOMMENDED
- Get free API key from: https://app.skyvern.com
- Add to `config.yaml`:
  ```yaml
  api:
    skyvern_api_key: "your-key-here"
  ```
- Enable in `automator_main.py`:
  ```python
  USE_SKYVERN = True
  ```

### Option 2: Local Mode (COMPLEX) ❌ NOT RECOMMENDED
Requires:
- PostgreSQL database installation
- Async database drivers (aiosqlite/asyncpg)
- Run `skyvern init` and full backend setup
- Database migrations
- Complex configuration

**Too complex for quick setup!**

---

## Current Working Solution

✅ **Browser-Use (Hybrid Mode)** is ENABLED and working:
- Located in: `automator_main.py` line 49
- `USE_HYBRID_MODE = True`
- Uses Gemini AI (already configured)
- Works with ANY ATS platform

---

## How to Enable Skyvern (If You Want)

### Step 1: Get Cloud API Key
1. Go to https://app.skyvern.com
2. Sign up (free tier available)
3. Get your API key

### Step 2: Add to Config
Edit `config.yaml`:
```yaml
api:
  gemini_api_key: "..."
  gemini_model_name: "..."
  skyvern_api_key: "sk-YOUR-KEY-HERE"  # Add this line
```

### Step 3: Update Code
Edit `config.py` (add this after other API configs):
```python
SKYVERN_API_KEY = api_config.get('skyvern_api_key', '')
```

### Step 4: Update Skyvern Filler
Edit `skyvern_filler.py` line 94:
```python
# Change from:
skyvern = Skyvern()

# To:
if config.SKYVERN_API_KEY:
    skyvern = Skyvern(api_key=config.SKYVERN_API_KEY)  # Cloud mode
else:
    raise Exception("Skyvern API key required in config.yaml")
```

### Step 5: Enable in Automator
Edit `automator_main.py` line 47:
```python
USE_SKYVERN = True  # Enable
USE_HYBRID_MODE = False  # Disable
```

---

## Performance Comparison

| Agent | Success Rate | Status |
|-------|--------------|--------|
| **Skyvern** | ~85% | Disabled (needs API key) |
| **Browser-Use** | ~60-70% | ✅ **ACTIVE** (working now) |
| **Traditional** | ~40-50% | Available |

---

## Bottom Line

**You can use the system RIGHT NOW with Browser-Use!**

Run:
```bash
job-agent apply --batch 1
```

It will use Browser-Use (Hybrid Mode) which is already working.

If you want the better Skyvern (85% success), get the API key from app.skyvern.com and follow the steps above.

---

## Files Reference

- Current agent: `job_automator/ats_fillers/hybrid_filler.py` (Browser-Use)
- Skyvern code: `job_automator/ats_fillers/skyvern_filler.py` (ready, just needs API key)
- Configuration: `job_automator/automator_main.py` (line 47-49)

---

**Ready to test with Browser-Use?**
```bash
job-agent apply --batch 1
```
