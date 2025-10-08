#!/bin/bash

# Function to resolve integer value or use default
resolve_int_or_default() {
    local value="$1"
    local default="$2"
    
    if [ -n "$value" ] && [[ "$value" =~ ^[0-9]+$ ]]; then
        echo "$value"
    else
        echo "$default"
    fi
}

# Get parameters with defaults
max_retries=$(resolve_int_or_default "$1" "$(resolve_int_or_default "$CAMOUFOX_MAX_RETRIES" "3")")
retry_delay=$(resolve_int_or_default "$2" "$(resolve_int_or_default "$CAMOUFOX_RETRY_DELAY" "10")")

for ((attempt=1; attempt<=max_retries; attempt++)); do
    camoufox fetch
    if [ $? -eq 0 ]; then
        echo "camoufox fetch succeeded on attempt $attempt."
        exit 0
    fi
    
    if [ $attempt -eq $max_retries ]; then
        echo "camoufox fetch failed after $max_retries attempts." >&2
        exit 1
    fi
    
    # Add jitter (0-4 seconds)
    jitter=$((RANDOM % 5))
    retry_delay_seconds=$((retry_delay + jitter))
    echo "camoufox fetch failed on attempt $attempt. Retrying in $retry_delay_seconds seconds..." >&2
    sleep $retry_delay_seconds
done