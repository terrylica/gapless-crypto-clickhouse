# Troubleshooting ClickHouse Cloud Connections

Complete troubleshooting guide for common errors when connecting to ClickHouse Cloud.

## Error 1: Connection Refused

**Symptoms**:
```
Exception: Failed to connect to ClickHouse at <host>:8443: Connection refused
OSError: [Errno 61] Connection refused
```

**Root Causes**:
1. **Wrong hostname format**: Not using ClickHouse Cloud hostname pattern
2. **Wrong port**: Using 8123 (local Docker) instead of 8443 (Cloud HTTPS)
3. **Service paused/stopped**: ClickHouse Cloud service not running

**Fix**:

1. **Verify hostname** ends with `.aws.clickhouse.cloud`:
   ```bash
   echo $CLICKHOUSE_HOST
   # Expected: ebmf8f35lu.us-west-2.aws.clickhouse.cloud
   # NOT: localhost or clickhouse.example.com
   ```

2. **Verify port** is 8443 (Cloud HTTPS), not 8123 (local HTTP):
   ```bash
   echo $CLICKHOUSE_HTTP_PORT
   # Expected: 8443
   # NOT: 8123
   ```

3. **Check service status** in ClickHouse Cloud console:
   - Visit: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2
   - Status should be "Running" (green)
   - If "Paused" or "Idle", service resuming takes ~10-30 seconds

4. **If service is resuming from idle** (15-minute idle scaling):
   - Wait 30 seconds
   - Retry connection
   - First query after idle always slower

---

## Error 2: SSL/TLS Certificate Error

**Symptoms**:
```
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
requests.exceptions.SSLError: HTTPSConnectionPool
clickhouse_connect.driver.exceptions.TLSError
```

**Root Cause**:
- Missing `secure=True` parameter in clickhouse-connect client
- Package version < 6.0.0 (doesn't support `CLICKHOUSE_SECURE` env var)

**Fix**:

1. **Verify `CLICKHOUSE_SECURE=true`** in environment:
   ```bash
   echo $CLICKHOUSE_SECURE
   # Expected: true
   # NOT: false or empty
   ```

2. **Check package version** (must be 6.0.0+ for ADR-0026 `secure` parameter support):
   ```bash
   pip show gapless-crypto-clickhouse | grep Version
   # Expected: 6.0.0 or higher
   ```

3. **Upgrade if needed**:
   ```bash
   pip install --upgrade gapless-crypto-clickhouse
   ```

4. **For older package versions** (workaround):
   - Manually create clickhouse-connect client with `secure=True`:
   ```python
   import clickhouse_connect
   client = clickhouse_connect.get_client(
       host=os.getenv("CLICKHOUSE_HOST"),
       port=int(os.getenv("CLICKHOUSE_HTTP_PORT", "8443")),
       username=os.getenv("CLICKHOUSE_USER", "default"),
       password=os.getenv("CLICKHOUSE_PASSWORD"),
       secure=True  # Explicit TLS/SSL
   )
   ```

---

## Error 3: Authentication Failed

**Symptoms**:
```
Exception: Authentication failed
clickhouse_connect.driver.exceptions.DatabaseError: Code: 516, Authentication failed: password is incorrect
Access denied for user 'default'
```

**Root Causes**:
1. **Wrong password**: Password doesn't match ClickHouse Cloud console
2. **Expired password**: Password was rotated but not updated in Doppler/.env
3. **Typo in password**: Copy-paste error or trailing whitespace

**Fix**:

1. **Verify password in Doppler** (if using Doppler):
   ```bash
   doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd --plain
   # Compare with ClickHouse Cloud console password
   ```

2. **Verify password in .env** (if using .env file):
   ```bash
   grep CLICKHOUSE_PASSWORD .env
   # Compare with ClickHouse Cloud console password
   # Ensure no trailing spaces or quotes
   ```

3. **Reset password in ClickHouse Cloud console**:
   - Visit: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2
   - Navigate to: Settings → Reset Password
   - Copy new password immediately
   - Update Doppler: `doppler secrets set CLICKHOUSE_PASSWORD "<new_password>" --project aws-credentials --config prd`
   - Update 1Password: Engineering vault → "ClickHouse Cloud - gapless-crypto-cli" item

4. **Check for trailing whitespace**:
   ```bash
   # Doppler
   doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd --plain | wc -c
   # Expected: password length only (no extra chars)

   # .env file
   cat .env | grep CLICKHOUSE_PASSWORD | sed 's/.*=//' | od -c
   # Look for trailing spaces or newlines
   ```

---

## Error 4: Timeout (>10 seconds)

**Symptoms**:
```
Exception: Timeout waiting for connection
requests.exceptions.ConnectTimeout
Connection timeout after 10 seconds
```

**Root Causes**:
1. **Service resuming from idle**: ClickHouse Cloud has 15-minute idle scaling
2. **Network issue**: Firewall blocking HTTPS (port 8443)
3. **DNS resolution failure**: Cannot resolve `*.aws.clickhouse.cloud` hostname

**Fix**:

1. **Service resuming from idle** (most common):
   - ClickHouse Cloud pauses after 15 minutes of inactivity
   - First query triggers service resume (~10-30 seconds)
   - **Solution**: Wait 30 seconds, retry connection

2. **Verify network connectivity**:
   ```bash
   # Test DNS resolution
   nslookup ebmf8f35lu.us-west-2.aws.clickhouse.cloud
   # Expected: IP address returned

   # Test HTTPS connectivity
   curl -I https://ebmf8f35lu.us-west-2.aws.clickhouse.cloud:8443
   # Expected: HTTP response (even if 400/401)
   ```

3. **Check firewall/proxy** (corporate networks):
   - Ensure HTTPS (port 8443) is allowed
   - May need to allowlist `*.clickhouse.cloud` domains

4. **Increase timeout** (if service consistently slow):
   ```python
   # Not recommended long-term, but useful for diagnosis
   from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
   import clickhouse_connect

   # Create client with custom timeout
   client = clickhouse_connect.get_client(
       host=os.getenv("CLICKHOUSE_HOST"),
       port=8443,
       username=os.getenv("CLICKHOUSE_USER"),
       password=os.getenv("CLICKHOUSE_PASSWORD"),
       secure=True,
       connect_timeout=60  # 60 seconds (default: 10)
   )
   ```

---

## Error 5: Table/Database Not Found

**Symptoms**:
```
clickhouse_connect.driver.exceptions.DatabaseError: Code: 60, Table gapless_crypto.klines doesn't exist
Code: 81, Database gapless_crypto doesn't exist
```

**Root Cause**:
- **Expected for new ClickHouse Cloud service**: Database schema not yet created

**Fix**:

1. **For `query_ohlcv()` API** (auto-creates schema):
   ```python
   import gapless_crypto_clickhouse as gcd

   # First query auto-creates database + table
   df = gcd.query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
   # This will create gapless_crypto.klines automatically
   ```

2. **For manual schema creation** (advanced):
   ```bash
   # Run schema migration from repo
   doppler run --project aws-credentials --config prd -- python -c "
   from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

   with ClickHouseConnection() as conn:
       # Create database
       conn.execute('CREATE DATABASE IF NOT EXISTS gapless_crypto')

       # Create table (see schema.sql for full definition)
       conn.execute('''
       CREATE TABLE IF NOT EXISTS gapless_crypto.klines (...) ENGINE = ReplacingMergeTree() ...
       ''')
   "
   ```

3. **Verify schema exists**:
   ```python
   from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

   with ClickHouseConnection() as conn:
       # List databases
       result = conn.execute("SHOW DATABASES")
       print("Databases:", [r[0] for r in result])

       # List tables in gapless_crypto
       result = conn.execute("SHOW TABLES FROM gapless_crypto")
       print("Tables:", [r[0] for r in result])
   ```

---

## Error 6: Package Import Failure

**Symptoms**:
```
ModuleNotFoundError: No module named 'gapless_crypto_clickhouse'
ImportError: cannot import name 'ClickHouseConnection'
```

**Root Cause**:
- Package not installed OR wrong Python environment

**Fix**:

1. **Install package**:
   ```bash
   pip install gapless-crypto-clickhouse
   ```

2. **Verify installation**:
   ```bash
   pip show gapless-crypto-clickhouse
   # Expected: Version 6.0.0+, Location shown
   ```

3. **Check Python environment** (if using virtual envs):
   ```bash
   which python
   pip list | grep gapless-crypto-clickhouse
   ```

4. **For uv users**:
   ```bash
   uv pip install gapless-crypto-clickhouse
   ```

---

## Error 7: Environment Variables Not Loaded

**Symptoms**:
```
ClickHouseConfig(host='localhost', port=9000, ..., secure=False)
# Wrong! Should be host='*.aws.clickhouse.cloud', port=8443, secure=True
```

**Root Cause**:
- Environment variables not set OR not loaded from Doppler/.env

**Fix**:

1. **Doppler method** - Verify Doppler is injecting env vars:
   ```bash
   # Check Doppler is working
   doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE
   # Expected: 8 secrets (CLICKHOUSE_HOST, CLICKHOUSE_PORT, etc.)

   # Run with Doppler
   doppler run --project aws-credentials --config prd -- env | grep CLICKHOUSE
   # Expected: All CLICKHOUSE_* vars printed
   ```

2. **.env file method** - Verify .env file is loaded:
   ```bash
   # Check .env exists
   ls -la .env
   # Expected: File exists

   # Check .env has credentials
   cat .env | grep CLICKHOUSE_
   # Expected: All CLICKHOUSE_* vars present

   # Load .env in Python
   python -c "
   from dotenv import load_dotenv
   import os
   load_dotenv('.env')
   print('Host:', os.getenv('CLICKHOUSE_HOST'))
   print('Secure:', os.getenv('CLICKHOUSE_SECURE'))
   "
   # Expected: Correct values printed
   ```

3. **Verify environment in code**:
   ```python
   from gapless_crypto_clickhouse.clickhouse import ClickHouseConfig

   config = ClickHouseConfig.from_env()
   print(config)
   # Expected: host='*.aws.clickhouse.cloud', port=8443, secure=True
   # NOT: host='localhost', port=8123, secure=False
   ```

---

## General Debugging Steps

1. **Check environment variables**:
   ```bash
   env | grep CLICKHOUSE
   # Expected: All required vars present with correct values
   ```

2. **Test connection with raw clickhouse-connect**:
   ```python
   import clickhouse_connect
   import os

   client = clickhouse_connect.get_client(
       host=os.getenv("CLICKHOUSE_HOST"),
       port=int(os.getenv("CLICKHOUSE_HTTP_PORT", "8443")),
       username=os.getenv("CLICKHOUSE_USER", "default"),
       password=os.getenv("CLICKHOUSE_PASSWORD"),
       secure=True
   )
   result = client.query("SELECT version()")
   print("ClickHouse version:", result.result_rows[0][0])
   ```

3. **Check ClickHouse Cloud console**:
   - Service status: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2
   - Verify service is "Running" (green)
   - Check idle timeout settings (15 minutes default)

4. **Review package logs** (if available):
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   # Re-run connection test, logs will show detailed connection info
   ```

5. **Ask for help**:
   - Join #data-engineering Slack
   - Provide error message + environment details (host, port, package version)

---

## Quick Reference

| Error | Most Likely Cause | Quick Fix |
|-------|-------------------|-----------|
| Connection refused | Wrong host/port | Check CLICKHOUSE_HOST ends with `.aws.clickhouse.cloud`, port 8443 |
| SSL/TLS error | Missing secure=True | Set CLICKHOUSE_SECURE=true, upgrade to v6.0.0+ |
| Authentication failed | Wrong password | Check Doppler/console password, reset if needed |
| Timeout | Service idle | Wait 30s, retry (service resuming) |
| Table not found | Schema not created | Expected for new service, query_ohlcv() auto-creates |
| Import error | Package not installed | pip install gapless-crypto-clickhouse |
| Env vars not loaded | Doppler/.env not working | Use `doppler run --` or load_dotenv('.env') |

---

**Last Updated**: 2025-11-21 (ADR-0026)
**Related**: [`SKILL.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/SKILL.md), [`doppler-setup.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/doppler-setup.md), [`env-setup.md`](/Users/terryli/eon/gapless-crypto-clickhouse/skills/gapless-crypto-clickhouse-onboarding/references/env-setup.md)
