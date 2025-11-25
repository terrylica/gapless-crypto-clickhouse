VERSION 0.8

# Base image with Python and validation dependencies
validation-base:
    FROM python:3.12-slim
    WORKDIR /workspace

    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        curl \
        git \
        && rm -rf /var/lib/apt/lists/*

    # Install GitHub CLI (gh)
    RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
        && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && apt-get update \
        && apt-get install gh -y

    # Install Python dependencies
    RUN pip install --no-cache-dir \
        clickhouse-connect>=0.7.0 \
        requests>=2.28.0 \
        packaging>=21.0

    # Copy validation scripts
    COPY scripts/validate_github_release.py .
    COPY scripts/validate_pypi_version.py .
    COPY scripts/validate_production_health.py .
    COPY scripts/write_validation_results.py .
    COPY scripts/send_pushover_notification.py .

# Validate GitHub Release exists
github-release-check:
    FROM +validation-base
    ARG RELEASE_VERSION
    ARG GIT_COMMIT=""
    ARG GITHUB_REPOSITORY="terrylica/gapless-crypto-clickhouse"

    RUN --secret GITHUB_TOKEN \
        export GITHUB_TOKEN && \
        python validate_github_release.py \
            --version "$RELEASE_VERSION" \
            --repository "$GITHUB_REPOSITORY" \
            --git-commit "$GIT_COMMIT" \
            --output github-release-result.json \
        || (echo "GitHub Release validation failed" && exit 0)

    SAVE ARTIFACT github-release-result.json AS LOCAL ./artifacts/

# Validate PyPI version matches release tag
pypi-version-check:
    FROM +validation-base
    ARG RELEASE_VERSION
    ARG GIT_COMMIT=""
    ARG PACKAGE_NAME="gapless-crypto-clickhouse"

    RUN python validate_pypi_version.py \
            --expected-version "$RELEASE_VERSION" \
            --package "$PACKAGE_NAME" \
            --git-commit "$GIT_COMMIT" \
            --output pypi-version-result.json \
        || (echo "PyPI version validation failed" && exit 0)

    SAVE ARTIFACT pypi-version-result.json AS LOCAL ./artifacts/

# Validate production environment health
production-health-check:
    FROM +validation-base
    ARG RELEASE_VERSION
    ARG GIT_COMMIT=""

    RUN --secret CLICKHOUSE_HOST \
        --secret CLICKHOUSE_PORT \
        --secret CLICKHOUSE_USER \
        --secret CLICKHOUSE_PASSWORD \
        export CLICKHOUSE_HOST && \
        export CLICKHOUSE_PORT && \
        export CLICKHOUSE_USER && \
        export CLICKHOUSE_PASSWORD && \
        python validate_production_health.py \
            --release-version "$RELEASE_VERSION" \
            --git-commit "$GIT_COMMIT" \
            --output production-health-result.json \
        || (echo "Production health validation failed" && exit 0)

    SAVE ARTIFACT production-health-result.json AS LOCAL ./artifacts/

# Write validation results to ClickHouse
write-to-clickhouse:
    FROM +validation-base
    COPY +github-release-check/github-release-result.json ./results/
    COPY +pypi-version-check/pypi-version-result.json ./results/
    COPY +production-health-check/production-health-result.json ./results/

    RUN --secret CLICKHOUSE_HOST \
        --secret CLICKHOUSE_PORT \
        --secret CLICKHOUSE_USER \
        --secret CLICKHOUSE_PASSWORD \
        export CLICKHOUSE_HOST && \
        export CLICKHOUSE_PORT && \
        export CLICKHOUSE_USER && \
        export CLICKHOUSE_PASSWORD && \
        python write_validation_results.py \
            --results-dir ./results/ \
        || (echo "ClickHouse write failed (non-fatal)" && exit 0)

# Send Pushover alert
send-pushover-alert:
    FROM +validation-base
    COPY +github-release-check/github-release-result.json ./results/
    COPY +pypi-version-check/pypi-version-result.json ./results/
    COPY +production-health-check/production-health-result.json ./results/
    ARG RELEASE_VERSION
    ARG GITHUB_RELEASE_URL

    RUN --secret PUSHOVER_APP_TOKEN \
        --secret PUSHOVER_USER_KEY \
        export PUSHOVER_APP_TOKEN && \
        export PUSHOVER_USER_KEY && \
        python send_pushover_notification.py \
            --results-dir ./results/ \
            --release-version "$RELEASE_VERSION" \
            --release-url "$GITHUB_RELEASE_URL" \
        || (echo "Pushover notification failed (non-fatal)" && exit 0)

# Main pipeline - orchestrates all validation targets
release-validation-pipeline:
    BUILD +github-release-check
    BUILD +pypi-version-check
    BUILD +production-health-check
    BUILD +write-to-clickhouse
    BUILD +send-pushover-alert
