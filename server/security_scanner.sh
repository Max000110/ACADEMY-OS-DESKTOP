#!/bin/bash
# AcademyOS Repository Security Scanner
set -e

echo "=== ACADEMYOS SECURITY SCANNER ==="
FAILED=0

# 1. Check for GitHub Personal Access Tokens (ghp_*)
echo "Scanning for GitHub Personal Access Tokens..."
if grep -rnEI -e "ghp_[A-Za-z0-9_]{36}" --exclude-dir={venv,.git,build,dist,tests,scratch} --exclude="*.log" . ; then
    echo "ERROR: Exposed GitHub Token (ghp_) detected!"
    FAILED=1
fi

# 2. Check for private signing keys or certificates
echo "Scanning for private keys..."
if grep -rnEI -e "---BEGIN [A-Z]+ PRIVATE KEY---" --exclude-dir={venv,.git,build,dist,tests,scratch} --exclude="*.log" . ; then
    echo "ERROR: Committed Private Key detected!"
    FAILED=1
fi

# 3. Check for raw public IP addresses in server configuration
echo "Scanning for public IPs..."
# Matches standard IPv4 format but excludes localhost/loopback/private IP prefixes
if grep -rnEI -e "\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b" --exclude-dir={venv,.git,build,dist,tests,scratch} --exclude="*.log" . | grep -vE "(127\.0\.0\.1|0\.0\.0\.0|192\.168\.|10\.)" ; then
    echo "ERROR: Hardcoded server/public IP address detected!"
    FAILED=1
fi

# 4. Check for DB password leaks or hardcoded secret variables
echo "Scanning for hardcoded secrets/passwords..."
if grep -rnEI -e "(password|secret|salt)\s*=\s*['\"][a-zA-Z0-9_\-]{8,}['\"]" --exclude-dir={venv,.git,build,dist,tests,scratch} --exclude="*.log" . | grep -vE "(dev_fallback|dev_jwt)" ; then
    echo "ERROR: Potential hardcoded secret/password detected!"
    FAILED=1
fi

if [ $FAILED -ne 0 ]; then
    echo "=== RESULT: SCAN FAILED (Security leaks found!) ==="
    exit 1
else
    echo "=== RESULT: SCAN PASSED (Clean repository) ==="
    exit 0
fi
