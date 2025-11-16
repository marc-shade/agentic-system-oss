# GitMQ Security - Quick Reference Card

Essential commands for daily operations with the secure GitMQ cluster.

## Setup (One-Time)

### Install Dependencies
```bash
pip3 install pydantic cryptography psutil
```

### Generate Node Keys
```bash
# Replace 'macpro51' with your node ID
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('macpro51')"
```

### Share Public Keys
```bash
# From mac-studio (orchestrator), collect and distribute all keys
cd ~/.ssh/cluster-keys

# Collect
for node in macpro51 macbook-air; do
    scp marc@${node}:~/.ssh/cluster-keys/${node}.pub .
done

# Distribute
for node in macpro51 macbook-air; do
    scp *.pub marc@${node}:~/.ssh/cluster-keys/
done
```

## Daily Operations

### Start Secure Daemon
```bash
cd ~/agentic-system/cluster-deployment

python3 github_node_daemon.py \
    --node-id macpro51 \
    --repo mjohnson518/agentic-cluster-comms \
    --poll-interval 30
```

### Check Daemon Status
```bash
ps aux | grep github_node_daemon
tail -f ~/agentic-system/logs/github-daemon.log
```

### Verify Trust
```bash
python3 -c "
from auth import MessageAuthenticator
auth = MessageAuthenticator('macpro51')  # Your node ID
print('Trusted nodes:', list(auth.public_keys.keys()))
"
```

Expected: All cluster nodes listed

### Run Security Tests
```bash
cd ~/agentic-system/cluster-deployment

# Full test suite
python3 test_security.py --node-id macpro51 --test-all

# Quick test
python3 test_security.py --node-id macpro51 --test-signing
```

## Creating Tasks

### Python Example
```python
from auth import MessageAuthenticator
from payload_schema import TaskPayload, TaskType

# Initialize
auth = MessageAuthenticator(node_id="macpro51")

# Create task
task = TaskPayload(
    type=TaskType.CODE_EXECUTION,
    source_node="macpro51",
    target_node="mac-studio",
    payload={
        "code": "import sys; print(sys.version)",
        "code_language": "python",
        "entry_point": "main.py"
    }
)

# Sign
signed_task = auth.sign_payload(task.model_dump(mode='json'))

# Commit to GitHub...
```

### Bash Example
```bash
# Use the task submission script (if created)
python3 submit_task.py \
    --source macpro51 \
    --target mac-studio \
    --type code_execution \
    --code "print('Hello')"
```

## Troubleshooting

### "No public key found"
```bash
# Check if public key exists
ls ~/.ssh/cluster-keys/

# If missing, copy from sender node
scp marc@sender-node:~/.ssh/cluster-keys/sender.pub ~/.ssh/cluster-keys/
```

### "Signature verification failed"
```bash
# Check trusted keys
python3 -c "
from auth import MessageAuthenticator
auth = MessageAuthenticator('macpro51')
print('Loaded keys:', list(auth.public_keys.keys()))
"

# Re-verify sender's key is present
ls ~/.ssh/cluster-keys/sender-node.pub
```

### "Schema validation failed"
```bash
# Test payload against schema
python3 -c "
from payload_schema import TaskPayload, validate_payload
from pydantic import ValidationError

payload = {...}  # Your payload here

try:
    task = validate_payload(payload, TaskPayload)
    print('Valid!')
except ValidationError as e:
    print('Errors:')
    for error in e.errors():
        print(f\"  - {error['loc']}: {error['msg']}\")
"
```

### View Daemon Logs
```bash
# Real-time
tail -f ~/agentic-system/logs/github-daemon.log

# Recent errors
grep -i error ~/agentic-system/logs/github-daemon.log | tail -20

# Signature failures
grep -i signature ~/agentic-system/logs/github-daemon.log
```

## Key Management

### Rotate Keys (After Compromise)
```bash
# 1. Remove old keys
rm ~/.ssh/cluster-keys/macpro51.priv
rm ~/.ssh/cluster-keys/macpro51.pub

# 2. Generate new keys
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('macpro51')"

# 3. Redistribute public key to all nodes
for node in mac-studio macbook-air; do
    scp ~/.ssh/cluster-keys/macpro51.pub marc@${node}:~/.ssh/cluster-keys/
done

# 4. Restart daemon
pkill -f github_node_daemon.py
python3 github_node_daemon.py --node-id macpro51 --repo ... &
```

### Revoke Node Access
```bash
# On all nodes, remove compromised node's public key
rm ~/.ssh/cluster-keys/compromised-node.pub

# Restart daemons to reload keys
```

### Backup Keys (Encrypted)
```bash
# Create encrypted backup
tar czf - ~/.ssh/cluster-keys/*.priv | \
    openssl enc -aes-256-cbc -salt -out cluster-keys-backup.tar.gz.enc

# Restore from backup
openssl enc -aes-256-cbc -d -in cluster-keys-backup.tar.gz.enc | \
    tar xzf -
```

## Health Checks

### Quick Health Check
```bash
# 1. Dependencies installed?
python3 -c "import pydantic, cryptography; print('✓ Dependencies OK')"

# 2. Keys exist?
ls ~/.ssh/cluster-keys/*.priv && echo '✓ Keys exist'

# 3. Daemon running?
pgrep -f github_node_daemon && echo '✓ Daemon running'

# 4. Can sign messages?
python3 -c "
from auth import MessageAuthenticator
auth = MessageAuthenticator('macpro51')
msg = auth.sign_payload({'test': True})
print('✓ Signing works')
"
```

### Full Diagnostic
```bash
cd ~/agentic-system/cluster-deployment
python3 test_security.py --node-id macpro51 --test-all
```

## Security Best Practices

### ✅ DO
- Keep private keys at 600 permissions
- Sign all outgoing messages
- Verify all incoming messages
- Use schema validation for all payloads
- Rotate keys after suspected compromise
- Keep backups encrypted
- Monitor logs for signature failures

### ❌ DON'T
- Share private keys (.priv files)
- Commit keys to Git
- Use shell=True in subprocess calls
- Accept unsigned messages
- Override PATH or other protected env vars
- Use future timestamps
- Allow directory traversal in paths

## File Locations

| File | Purpose | Permissions |
|------|---------|-------------|
| `~/.ssh/cluster-keys/*.priv` | Private keys (NEVER share!) | 600 |
| `~/.ssh/cluster-keys/*.pub` | Public keys (share with all nodes) | 644 |
| `~/agentic-system/logs/github-daemon.log` | Daemon logs | 644 |
| `~/agentic-system/cluster-deployment/auth.py` | Authentication module | 644 |
| `~/agentic-system/cluster-deployment/payload_schema.py` | Schema validation | 644 |
| `~/agentic-system/cluster-deployment/github_node_daemon.py` | Secure daemon | 755 |

## Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| "Signature verification failed" | Message not from trusted node | Share sender's .pub key |
| "No public key found for node: X" | Missing sender's public key | Copy sender's .pub to ~/.ssh/cluster-keys/ |
| "Schema validation failed" | Invalid payload format | Check payload against schema |
| "Shell injection blocked" | Dangerous characters in args | Remove shell metacharacters |
| "Directory traversal blocked" | Path contains .. or /etc | Use safe relative paths |
| "Timestamp cannot be in future" | Clock skew or attack | Check system time |

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Sign message | <1ms | Ed25519 is very fast |
| Verify signature | <1ms | Faster than RSA |
| Schema validation | 1-2ms | Pydantic overhead |
| Total task overhead | <5ms | Negligible |

## Support Resources

- **Setup Guide**: `SECURITY_SETUP.md`
- **Implementation Roadmap**: `IMPLEMENTATION_ROADMAP.md`
- **Phase 0 Summary**: `PHASE_0_COMPLETE.md`
- **Test Suite**: `python3 test_security.py --help`
- **Logs**: `~/agentic-system/logs/github-daemon.log`

---

**Quick Help**: `python3 test_security.py --help`
**Full Docs**: `SECURITY_SETUP.md`

Last updated: November 16, 2025
