# Doppler Secrets Schema for gapless-crypto-clickhouse

**Project**: `aws-credentials`
**Config**: `prd`

## Required Secrets (8 total)

### API Credentials

| Secret Name | Description | Format | Example |
|-------------|-------------|--------|---------|
| `CLICKHOUSE_CLOUD_KEY_ID` | ClickHouse Cloud API Key ID | Alphanumeric, ~20 chars | `xnIdJM3n42LDImsZ9zzg` |
| `CLICKHOUSE_CLOUD_KEY_SECRET` | ClickHouse Cloud API Key Secret | Alphanumeric, ~40 chars | (secured in Doppler) |

**Source**: ClickHouse Cloud Console → Settings → API Keys
**Usage**: HTTP Basic Auth for ClickHouse Cloud API calls

### Service Metadata

| Secret Name | Description | Format | Example |
|-------------|-------------|--------|---------|
| `CLICKHOUSE_CLOUD_ORG_ID` | Organization UUID | UUID (8-4-4-4-12) | `2404d339-6921-4f1c-bf80-b07d5e23b91a` |
| `CLICKHOUSE_CLOUD_SERVICE_ID` | Service UUID (gapless-crypto-clickhouse) | UUID (8-4-4-4-12) | `a3163f31-21f4-4e22-844e-ef3fbc26ace2` |

**Source**: ClickHouse Cloud API (`GET /organizations`, service dashboard)
**Usage**: API endpoints for service management

### Connection Parameters

| Secret Name | Description | Format | Example |
|-------------|-------------|--------|---------|
| `CLICKHOUSE_HOST` | Service hostname | FQDN | `ebmf8f35lu.us-west-2.aws.clickhouse.cloud` |
| `CLICKHOUSE_PORT` | HTTPS port | Integer | `8443` |
| `CLICKHOUSE_USER` | Database username | String | `default` |
| `CLICKHOUSE_PASSWORD` | Database password | Alphanumeric | (secured in Doppler) |

**Source**: ClickHouse Cloud API service details, console
**Usage**: clickhouse-connect client configuration

## Storage Commands

```bash
# API Credentials
doppler secrets set CLICKHOUSE_CLOUD_KEY_ID "<key_id>" --project aws-credentials --config prd
doppler secrets set CLICKHOUSE_CLOUD_KEY_SECRET "<key_secret>" --project aws-credentials --config prd

# Service Metadata
doppler secrets set CLICKHOUSE_CLOUD_ORG_ID "<org_id>" --project aws-credentials --config prd
doppler secrets set CLICKHOUSE_CLOUD_SERVICE_ID "a3163f31-21f4-4e22-844e-ef3fbc26ace2" --project aws-credentials --config prd

# Connection Parameters
doppler secrets set CLICKHOUSE_HOST "ebmf8f35lu.us-west-2.aws.clickhouse.cloud" --project aws-credentials --config prd
doppler secrets set CLICKHOUSE_PORT "8443" --project aws-credentials --config prd
doppler secrets set CLICKHOUSE_USER "default" --project aws-credentials --config prd
doppler secrets set CLICKHOUSE_PASSWORD "<db_password>" --project aws-credentials --config prd
```

## Usage Pattern

```bash
# Load all secrets into environment
doppler run --project aws-credentials --config prd -- python your_script.py

# Or export to file
doppler secrets download --project aws-credentials --config prd --no-file --format env > .env
```

## Verification

```bash
# List secret names (no values)
doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE

# Expected output:
# CLICKHOUSE_CLOUD_KEY_ID
# CLICKHOUSE_CLOUD_KEY_SECRET
# CLICKHOUSE_CLOUD_ORG_ID
# CLICKHOUSE_CLOUD_SERVICE_ID
# CLICKHOUSE_HOST
# CLICKHOUSE_PORT
# CLICKHOUSE_USER
# CLICKHOUSE_PASSWORD
```

## Reference

- **Doppler Dashboard**: https://dashboard.doppler.com/workplace/13e9e4203ede563b1d37/projects/aws-credentials
- **Doppler CLI Docs**: https://docs.doppler.com/docs/install-cli
