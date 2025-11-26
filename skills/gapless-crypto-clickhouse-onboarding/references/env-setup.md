# Local .env File Setup for ClickHouse Cloud Access

Complete guide for local `.env` file configuration (fallback method when Doppler is not available or preferred).

## Overview

**Local `.env` file** stores ClickHouse Cloud credentials on disk for development.

**Use When**:
- Doppler CLI not available (e.g., external contractors, CI/CD systems without Doppler integration)
- Offline development (no Doppler API access)
- IDE integration requiring local environment files

**Security Trade-offs**:
- ⚠️ Credentials stored on disk (less secure than Doppler)
- ⚠️ Manual rotation (must update file when passwords change)
- ✅ Simpler for one-off scripts (no `doppler run --` prefix)
- ✅ Works offline (no Doppler API dependency)

---

## Setup Steps

### Step 1: Copy Cloud Template

```bash
# Copy .env.cloud template to .env
cp .env.cloud .env

# Verify .env created
ls -la .env
```

### Step 2: Edit .env with Credentials

Open `.env` in your editor and fill in the required credentials:

```bash
# Required fields (MUST be filled in)
CLICKHOUSE_HOST=ebmf8f35lu.us-west-2.aws.clickhouse.cloud
CLICKHOUSE_HTTP_PORT=8443
CLICKHOUSE_DATABASE=default
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=<YOUR_PASSWORD_HERE>  # Get from Doppler or ClickHouse Cloud console
CLICKHOUSE_SECURE=true

# Optional fields (for advanced use cases)
CLICKHOUSE_CLOUD_KEY_ID=<API_KEY_ID>
CLICKHOUSE_CLOUD_KEY_SECRET=<API_KEY_SECRET>
CLICKHOUSE_CLOUD_ORG_ID=2404d339-6921-4f1c-bf80-b07d5e23b91a
CLICKHOUSE_CLOUD_SERVICE_ID=a3163f31-21f4-4e22-844e-ef3fbc26ace2
```

**Where to get password**:

**Option A: From Doppler** (if you have access):
```bash
doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd --plain
```

**Option B: From ClickHouse Cloud console**:
1. Visit: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2
2. Navigate to: Settings → Reset Password
3. Copy new password
4. Paste into `.env` file

### Step 3: Verify .env Format

**Common mistakes**:

❌ **Wrong**: Spaces around `=`
```bash
CLICKHOUSE_HOST = ebmf8f35lu.us-west-2.aws.clickhouse.cloud
```

✅ **Correct**: No spaces
```bash
CLICKHOUSE_HOST=ebmf8f35lu.us-west-2.aws.clickhouse.cloud
```

❌ **Wrong**: Quotes (usually not needed)
```bash
CLICKHOUSE_PASSWORD="my_password"
```

✅ **Correct**: No quotes
```bash
CLICKHOUSE_PASSWORD=my_password
```

❌ **Wrong**: Trailing whitespace
```bash
CLICKHOUSE_PASSWORD=my_password
# Invisible spaces after password!
```

✅ **Correct**: No trailing whitespace
```bash
CLICKHOUSE_PASSWORD=my_password
```

**Validation script**:
```bash
# Check for common formatting issues
cat .env | grep -E "(^[A-Z_]+\s*=\s*$|^\s*#|^\s*$)" && echo "⚠️  Warning: Empty or commented lines found"

# Check for trailing whitespace
grep -E '\s+$' .env && echo "⚠️  Warning: Trailing whitespace found"

# Verify all required vars present
for var in CLICKHOUSE_HOST CLICKHOUSE_HTTP_PORT CLICKHOUSE_USER CLICKHOUSE_PASSWORD CLICKHOUSE_SECURE; do
  grep -q "^${var}=" .env || echo "❌ Missing: $var"
done
```

### Step 4: Secure .env File

**Set restrictive permissions** (prevent other users from reading):

```bash
# Make .env readable only by you
chmod 600 .env

# Verify permissions
ls -la .env
# Expected: -rw------- (only owner can read/write)
```

**Verify .env is in .gitignore**:

```bash
# Check .gitignore
grep "^\.env$" .gitignore

# If missing, add it
echo ".env" >> .gitignore
```

**NEVER commit .env to version control**:

```bash
# Verify .env is ignored by git
git status
# .env should NOT appear in "Untracked files" or "Changes to be committed"

# If .env appears, add to .gitignore immediately
echo ".env" >> .gitignore
git add .gitignore
git commit -m "chore: add .env to .gitignore"
```

---

## Using .env File with Python

### Method 1: python-dotenv (Recommended)

**Install python-dotenv**:
```bash
pip install python-dotenv
```

**Load .env in Python script**:
```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv(".env")  # or load_dotenv() if .env in current directory

# Verify credentials loaded
print("Host:", os.getenv("CLICKHOUSE_HOST"))
print("Secure:", os.getenv("CLICKHOUSE_SECURE"))

# Use package normally
import gapless_crypto_clickhouse as gcch
df = gcch.query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
print(df.head())
```

**Connection test**:
```bash
python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py
# Script auto-detects .env file if present
```

### Method 2: Manual export (Shell)

**Export to shell environment**:
```bash
# Load .env into current shell
export $(cat .env | xargs)

# Verify
env | grep CLICKHOUSE

# Run scripts normally
python your_script.py
```

**Warning**: Credentials persist in shell environment. Exit shell when done.

### Method 3: direnv (Auto-loading)

**Install direnv** (auto-loads .env when entering directory):

```bash
# macOS (Homebrew)
brew install direnv

# Add to shell config (~/.zshrc or ~/.bashrc)
eval "$(direnv hook zsh)"  # or bash

# Allow .env in directory
echo "dotenv .env" > .envrc
direnv allow .

# Now .env auto-loads when entering directory
```

---

## Verifying .env Configuration

### Test 1: Environment Variables Loaded

```bash
# Install python-dotenv if needed
pip install python-dotenv

# Verify .env loaded correctly
python -c "
from dotenv import load_dotenv
import os

load_dotenv('.env')

required = ['CLICKHOUSE_HOST', 'CLICKHOUSE_HTTP_PORT', 'CLICKHOUSE_USER', 'CLICKHOUSE_PASSWORD', 'CLICKHOUSE_SECURE']
missing = [v for v in required if not os.getenv(v)]

if missing:
    print(f'❌ Missing env vars: {missing}')
else:
    print('✅ All required env vars loaded')
    print(f'   Host: {os.getenv(\"CLICKHOUSE_HOST\")}')
    print(f'   Port: {os.getenv(\"CLICKHOUSE_HTTP_PORT\")}')
    print(f'   Secure: {os.getenv(\"CLICKHOUSE_SECURE\")}')
"
```

### Test 2: ClickHouse Connection

```bash
# Run connection test
python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py

# Expected output:
# 🔍 Found .env file, loading credentials...
# ✅ .env file loaded
# ...
# ✅ Connection successful!
```

### Test 3: Package Query

```python
from dotenv import load_dotenv
load_dotenv('.env')

import gapless_crypto_clickhouse as gcch
from gapless_crypto_clickhouse.clickhouse import ClickHouseConfig

# Check config
config = ClickHouseConfig.from_env()
print("Config:", config)
# Expected: host='*.aws.clickhouse.cloud', port=8443, secure=True

# Test query
df = gcch.query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-02')
print(f"✅ Query successful: {len(df)} rows")
```

---

## Updating Credentials

### When to Update

- Password rotated in ClickHouse Cloud console
- Credentials changed in Doppler (sync to local .env)
- Service migrated to new hostname

### Update Process

1. **Get new password**:
   ```bash
   # Option A: From Doppler
   doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd --plain

   # Option B: From ClickHouse Cloud console
   # Visit: https://clickhouse.cloud/ → Settings → Reset Password
   ```

2. **Update .env file**:
   ```bash
   # Edit .env with new password
   # CLICKHOUSE_PASSWORD=<new_password>
   ```

3. **Test connection**:
   ```bash
   python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py
   ```

---

## Common Issues

### Issue 1: .env file not found

```
FileNotFoundError: [Errno 2] No such file or directory: '.env'
```

**Fix**:
```bash
# Check .env exists
ls -la .env

# If missing, copy template
cp .env.cloud .env
# Edit .env with your credentials
```

### Issue 2: Credentials not loaded

```python
# Config shows localhost instead of Cloud hostname
ClickHouseConfig(host='localhost', port=9000, secure=False)
```

**Fix**:
```python
# Ensure load_dotenv() is called BEFORE importing package
from dotenv import load_dotenv
load_dotenv('.env')  # MUST be before gapless_crypto_clickhouse import

import gapless_crypto_clickhouse as gcch
```

### Issue 3: Trailing whitespace in password

```
Exception: Authentication failed
```

**Fix**:
```bash
# Check for trailing whitespace
cat .env | grep CLICKHOUSE_PASSWORD | od -c
# Look for spaces or newlines after password

# Remove trailing whitespace
sed -i.bak 's/[[:space:]]*$//' .env
```

### Issue 4: python-dotenv not installed

```
ModuleNotFoundError: No module named 'dotenv'
```

**Fix**:
```bash
pip install python-dotenv
```

---

## Security Best Practices

1. **Never commit .env to git**:
   - Always in `.gitignore`
   - Verify with `git status` before committing

2. **Restrict file permissions**:
   ```bash
   chmod 600 .env  # Only owner can read/write
   ```

3. **Delete .env when not needed**:
   ```bash
   # Prefer Doppler for production
   # Use .env only for local development
   rm .env  # Delete when switching to Doppler
   ```

4. **Use .env.example for documentation**:
   ```bash
   # Create .env.example (no secrets)
   cp .env .env.example
   # Replace actual values with placeholders
   # Commit .env.example to git (safe to share)
   ```

5. **Rotate credentials regularly**:
   - Update .env when Doppler credentials change
   - Test connection after rotation

---

## Migrating from .env to Doppler

**When to migrate**:
- Team grows beyond 3-5 users
- Need centralized credential rotation
- Security audit requires credential management system

**Migration steps**:

1. **Verify Doppler access**:
   ```bash
   doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE
   ```

2. **Test Doppler connection**:
   ```bash
   doppler run --project aws-credentials --config prd -- python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py
   ```

3. **Update scripts to use Doppler**:
   ```bash
   # Old (.env file)
   python your_script.py

   # New (Doppler)
   doppler run --project aws-credentials --config prd -- python your_script.py
   ```

4. **Delete .env file** (credentials now in Doppler):
   ```bash
   rm .env
   ```

5. **Update documentation**:
   - Add "use Doppler" to README
   - Remove .env file instructions

---

## Next Steps

After setting up .env file:

1. **Test connection**: `python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py`
2. **Run first query**: See [`SKILL.md` Step 5](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/SKILL.md#step-5-run-first-query-5-minutes)
3. **If errors**: See [`troubleshooting.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/troubleshooting.md)
4. **Consider migrating to Doppler**: See [`doppler-setup.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/doppler-setup.md)

---

**Last Updated**: 2025-11-21 (ADR-0026)
**Related**: [`SKILL.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/SKILL.md), [`doppler-setup.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/doppler-setup.md), [`troubleshooting.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/troubleshooting.md)
