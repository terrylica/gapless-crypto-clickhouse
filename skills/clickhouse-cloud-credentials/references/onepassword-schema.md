# 1Password Item Schema for ClickHouse Cloud Credentials

**Vault**: Engineering
**Vault ID**: `<OP_VAULT_ID>`
**Item Title**: "<OP_ITEM_TITLE>"
**Category**: API Credential

## Required Fields (8 total)

| Field Name | Field Type | Description | Example Value |
|------------|------------|-------------|---------------|
| `username` | text | API Key ID | `xnIdJM3n42LDImsZ9zzg` |
| `credential` | concealed | API Key Secret | (secured, ~40 chars) |
| `organization_id` | text | Organization UUID | `<CLICKHOUSE_ORG_ID>` |
| `organization_name` | text | Organization name | `TE's Organization` |
| `service_id` | text | Service UUID | `<CLICKHOUSE_SERVICE_ID>` |
| `service_name` | text | Service name | `gapless-crypto-cli` |
| `database_password` | password | ClickHouse database password | (secured) |
| `console_url` | url | ClickHouse Cloud console | `https://clickhouse.cloud/` |

## Creation Command

```bash
# Create 1Password item
op item create --vault Engineering \
  --category "API Credential" \
  --title "<OP_ITEM_TITLE>" \
  username="<key_id>" \
  credential="<key_secret>" \
  "organization_id[text]=<org_id>" \
  "organization_name[text]=TE's Organization" \
  "service_id[text]=<CLICKHOUSE_SERVICE_ID>" \
  "service_name[text]=gapless-crypto-cli" \
  "database_password[password]=<db_password>" \
  "console_url[url]=https://clickhouse.cloud/"
```

## Retrieval Commands

```bash
# View item (non-sensitive fields)
op item get "<OP_ITEM_TITLE>" --vault Engineering

# Get specific field value
op item get "<OP_ITEM_TITLE>" --vault Engineering --fields username

# Reveal concealed/password fields
op item get "<OP_ITEM_TITLE>" --vault Engineering --reveal
```

## Update Commands

```bash
# Update organization ID
op item edit "<OP_ITEM_TITLE>" \
  "organization_id[text]=<new_org_id>" \
  --vault Engineering

# Update database password
op item edit "<OP_ITEM_TITLE>" \
  "database_password[password]=<new_password>" \
  --vault Engineering
```

## Verification

```bash
# List fields (non-sensitive)
op item get "<OP_ITEM_TITLE>" --vault Engineering | grep -E "service_id|organization_id|console_url"

# Expected output includes:
#   service_id:           <CLICKHOUSE_SERVICE_ID>
#   service_name:         gapless-crypto-cli
#   organization_id:      <CLICKHOUSE_ORG_ID>
#   organization_name:    TE's Organization
#   console_url:          https://clickhouse.cloud/
```

## Notes

- **Backup Purpose**: 1Password serves as secure backup for Doppler secrets
- **Team Access**: Engineering vault for team credential sharing
- **Field Types**:
  - `text`: Plain text (visible in item view)
  - `concealed`: Hidden by default (API secrets)
  - `password`: Encrypted password field (database passwords)
  - `url`: URL field with link validation

## Reference

- **1Password CLI Docs**: https://developer.1password.com/docs/cli/
- **Engineering Vault**: Access via 1Password desktop app or CLI
