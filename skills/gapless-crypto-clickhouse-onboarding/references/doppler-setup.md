# Doppler Setup for ClickHouse Cloud Access

Complete guide for accessing ClickHouse Cloud credentials via Doppler CLI (recommended method for company employees).

## Overview

**Doppler** is the centralized credential management system for ClickHouse Cloud access. All 8 required credentials are stored in:

- **Project**: `aws-credentials`
- **Config**: `prd` (production)

**Advantages**:
- ✅ No local credential storage (credentials never touch disk)
- ✅ Centralized rotation (update once, affects all users)
- ✅ Team access control (managed by DevOps)
- ✅ Audit trail (who accessed what, when)

---

## Prerequisites

1. **Doppler CLI installed**:
   ```bash
   # macOS (Homebrew)
   brew install doppler

   # Linux (apt)
   curl -sLf --retry 3 --tlsv1.2 --proto "=https" https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key | sudo apt-key add -
   echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/doppler-cli.list
   sudo apt-get update && sudo apt-get install doppler

   # Verify installation
   doppler --version
   ```

2. **Doppler account authentication**:
   ```bash
   # Login to Doppler (opens browser)
   doppler login

   # Verify authentication
   doppler whoami
   # Expected: Your email address
   ```

3. **Access to `aws-credentials` project** (request from DevOps if missing)

---

## Verifying Access

### Step 1: List Available Projects

```bash
doppler projects
# Expected output includes: aws-credentials
```

If `aws-credentials` is missing → Contact DevOps team for access.

### Step 2: List Configs in Project

```bash
doppler configs --project aws-credentials
# Expected output includes: prd
```

### Step 3: Verify ClickHouse Secrets Exist

```bash
doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE
```

**Expected output** (8 secrets):
```
CLICKHOUSE_CLOUD_KEY_ID
CLICKHOUSE_CLOUD_KEY_SECRET
CLICKHOUSE_CLOUD_ORG_ID
CLICKHOUSE_CLOUD_SERVICE_ID
CLICKHOUSE_HOST
CLICKHOUSE_HTTP_PORT
CLICKHOUSE_USER
CLICKHOUSE_PASSWORD
```

If any secrets are missing → Contact DevOps team.

---

## Using Doppler with Python Scripts

### Method 1: `doppler run --` (Recommended)

Inject credentials as environment variables for a single command:

```bash
# Run Python script with Doppler credentials
doppler run --project aws-credentials --config prd -- python your_script.py

# Example: Connection test
doppler run --project aws-credentials --config prd -- python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py

# Example: Query OHLCV data
doppler run --project aws-credentials --config prd -- python -c "
import gapless_crypto_clickhouse as gcch
df = gcch.query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
print(df.head())
"
```

**Advantages**:
- Credentials never touch disk
- No `.env` file needed
- Most secure method

### Method 2: `doppler setup` + `doppler run` (Convenience)

Configure default project once, then use shorter commands:

```bash
# One-time setup in project directory
cd /path/to/project
doppler setup --project aws-credentials --config prd

# Now you can use shorter commands
doppler run -- python your_script.py
doppler run -- pytest tests/

# Configuration is stored in .doppler.yaml (safe to commit)
```

**Note**: `.doppler.yaml` only contains project/config names, NOT secrets.

### Method 3: Export to Environment (Not Recommended)

Export secrets to shell environment (credentials persist in session):

```bash
# Export all secrets to current shell
eval $(doppler secrets download --project aws-credentials --config prd --format env-no-quotes)

# Now run scripts normally
python your_script.py

# Check environment
env | grep CLICKHOUSE
```

**Warning**: Credentials persist in shell history and environment. Use Method 1 or 2 instead.

---

## Viewing Secret Values

### View All Secrets (Masked)

```bash
doppler secrets --project aws-credentials --config prd
# Shows names + masked values (****)
```

### View Specific Secret (Plain Text)

```bash
# Get single secret value
doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd --plain

# Get multiple secrets
doppler secrets get CLICKHOUSE_HOST CLICKHOUSE_HTTP_PORT --project aws-credentials --config prd --plain
```

**Security Note**: Use `--plain` only when needed (e.g., debugging, manual verification).

---

## Downloading Secrets to .env (Fallback)

If you need a local `.env` file (e.g., IDE integration, offline development):

```bash
# Download all secrets to .env file
doppler secrets download --project aws-credentials --config prd --format env > .env

# Verify .env created
ls -la .env

# IMPORTANT: Ensure .env is in .gitignore
grep "^\.env$" .gitignore
```

**Security Checklist**:
- [ ] `.env` is in `.gitignore` (NEVER commit credentials)
- [ ] `.env` has restricted permissions: `chmod 600 .env`
- [ ] `.env` is deleted when no longer needed
- [ ] Prefer `doppler run --` over `.env` file when possible

---

## Common Issues

### Issue 1: "Project not found"

```
Error: project aws-credentials not found
```

**Fix**: Request access from DevOps team.

### Issue 2: "Config not found"

```
Error: config prd not found in project aws-credentials
```

**Fix**:
1. List available configs: `doppler configs --project aws-credentials`
2. Use correct config name (may be `production` instead of `prd`)
3. Contact DevOps if `prd` config is missing

### Issue 3: "Authentication required"

```
Error: you must be authenticated to run this command
```

**Fix**:
```bash
doppler login
doppler whoami  # Verify authentication
```

### Issue 4: Doppler CLI not found

```
bash: doppler: command not found
```

**Fix**: Install Doppler CLI (see Prerequisites above)

---

## Best Practices

1. **Always use `doppler run --`** instead of downloading `.env` files
   - More secure (credentials never touch disk)
   - Automatic credential rotation (no manual updates)

2. **Use `doppler setup`** for convenience in projects you work on frequently
   - Configures default project/config
   - Shorter commands: `doppler run -- python script.py`

3. **Never commit Doppler secrets** to version control
   - `.env` files should be in `.gitignore`
   - `.doppler.yaml` is safe to commit (only contains project/config names)

4. **Verify access before onboarding others**:
   ```bash
   doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE | wc -l
   # Expected: 8 secrets
   ```

5. **Use secret audit logs** (if available):
   - Doppler dashboard → Audit Logs
   - Track who accessed which secrets when

---

## Credential Schema

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `CLICKHOUSE_CLOUD_KEY_ID` | ClickHouse Cloud API Key ID | `xnIdJM3n42LDImsZ9zzg` |
| `CLICKHOUSE_CLOUD_KEY_SECRET` | ClickHouse Cloud API Key Secret | (secured, ~40 chars) |
| `CLICKHOUSE_CLOUD_ORG_ID` | Organization UUID | `2404d339-6921-4f1c-bf80-b07d5e23b91a` |
| `CLICKHOUSE_CLOUD_SERVICE_ID` | Service UUID | `a3163f31-21f4-4e22-844e-ef3fbc26ace2` |
| `CLICKHOUSE_HOST` | Service hostname | `ebmf8f35lu.us-west-2.aws.clickhouse.cloud` |
| `CLICKHOUSE_HTTP_PORT` | HTTPS port | `8443` |
| `CLICKHOUSE_USER` | Database user | `default` |
| `CLICKHOUSE_PASSWORD` | Database password | (secured, from console) |

**Note**: First 4 secrets are for ClickHouse Cloud Management API (advanced use cases). Last 4 are for database connections (required).

---

## Next Steps

After verifying Doppler access:

1. **Test connection**: `doppler run --project aws-credentials --config prd -- python skills/gapless-crypto-clickhouse-onboarding/scripts/test_connection_cloud.py`
2. **Run first query**: See [`SKILL.md` Step 5](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/SKILL.md#step-5-run-first-query-5-minutes)
3. **If errors**: See [`troubleshooting.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/troubleshooting.md)

---

**Last Updated**: 2025-11-21 (ADR-0026)
**Related**: [`SKILL.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/SKILL.md), [`env-setup.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/env-setup.md), [`troubleshooting.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/troubleshooting.md)
