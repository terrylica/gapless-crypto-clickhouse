# ClickHouse Cloud API Endpoints Reference

**Base URL**: `https://api.clickhouse.cloud/v1`

**Authentication**: HTTP Basic Auth with `KEY_ID:KEY_SECRET`

## Organizations

### List Organizations

```bash
GET /organizations
```

**Response**:
```json
[
  {
    "id": "2404d339-6921-4f1c-bf80-b07d5e23b91a",
    "name": "TE's Organization",
    "createdAt": "2025-11-21T06:12:07Z",
    "privateEndpoints": []
  }
]
```

## Services

### Get Service Details

```bash
GET /organizations/{org_id}/services/{service_id}
```

**Parameters**:
- `org_id`: Organization UUID
- `service_id`: Service UUID (gapless-crypto-clickhouse: `a3163f31-21f4-4e22-844e-ef3fbc26ace2`)

**Response Schema**:
```json
{
  "result": {
    "id": "a3163f31-21f4-4e22-844e-ef3fbc26ace2",
    "name": "My first service",
    "provider": "aws",
    "region": "us-west-2",
    "state": "running",
    "endpoints": [
      {
        "protocol": "nativesecure",
        "host": "ebmf8f35lu.us-west-2.aws.clickhouse.cloud",
        "port": 9440
      },
      {
        "protocol": "https",
        "host": "ebmf8f35lu.us-west-2.aws.clickhouse.cloud",
        "port": 8443
      }
    ],
    "idleScaling": true,
    "idleTimeoutMinutes": 15,
    "minReplicaMemoryGb": 8,
    "maxReplicaMemoryGb": 8,
    "minTotalMemoryGb": 24,
    "maxTotalMemoryGb": 24,
    "numReplicas": 1,
    "ipAccessList": [
      {
        "source": "0.0.0.0/0",
        "description": "Anywhere"
      }
    ],
    "createdAt": "2025-11-21T06:23:50Z",
    "clickhouseVersion": "25.8",
    "iamRole": "arn:aws:iam::711387114042:role/CH-S3-violetaws-bc-49-uw2-83-Role"
  }
}
```

## Key Fields

- **state**: `running` | `idle` | `stopped`
- **endpoints[].protocol**: `https` (recommended for clickhouse-connect) | `nativesecure` (for clickhouse-client)
- **endpoints[].port**: `8443` (HTTPS) | `9440` (Native)
- **idleScaling**: Auto-pause after `idleTimeoutMinutes`
- **ipAccessList**: IP whitelist (`0.0.0.0/0` = open)

## Reference

- **ClickHouse Cloud API Docs**: https://clickhouse.com/docs/en/cloud/manage/api/api-overview
- **Console**: https://clickhouse.cloud/
