# GitMQ Cluster Security Setup

Complete guide for setting up cryptographic authentication and secure communication in the GitMQ cluster.

## Security Improvements

The GitMQ daemon now includes comprehensive security hardening:

### ✅ Fixed Vulnerabilities

1. **🔴 CRITICAL: Removed `shell=True`** (CVE-level vulnerability)
   - Previously allowed arbitrary command injection
   - Now uses proper argument lists
   - **Impact**: Prevents remote code execution

2. **🔐 Cryptographic Message Signatures**
   - Ed25519 signatures on all messages
   - Verifies sender identity
   - Detects tampering
   - **Impact**: Prevents message forgery and MITM attacks

3. **📋 Schema Validation**
   - Pydantic models for all payloads
   - Type checking and constraints
   - Prevents malformed data
   - **Impact**: Blocks malicious payloads

4. **🔒 Sandboxed Execution**
   - Isolated workspace directories
   - Resource limits (timeout, memory)
   - Restricted environment variables
   - **Impact**: Contains damage from malicious code

5. **🚫 Attack Prevention**
   - Directory traversal blocked
   - Shell injection prevented
   - Future timestamp rejection
   - Protected env vars
   - **Impact**: Hardens against common exploits

## Quick Start

### 1. Install Dependencies

```bash
cd /mnt/agentic-system/cluster-deployment

# Install required packages
pip3 install pydantic cryptography psutil
```

### 2. Generate Node Keys

On **each cluster node**, generate a keypair:

```bash
# On macpro51
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('macpro51')"

# On mac-studio
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('mac-studio')"

# On macbook-air
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('macbook-air')"
```

This creates:
- `~/.ssh/cluster-keys/{node-id}.priv` - Private key (never share!)
- `~/.ssh/cluster-keys/{node-id}.pub` - Public key (share with all nodes)

### 3. Share Public Keys

**Option A: Shared Filesystem** (if nodes share ~/. ssh)

Public keys are automatically discovered if all nodes mount the same `~/.ssh/cluster-keys/` directory.

**Option B: Manual Transfer** (most secure)

On each node, copy all other nodes' public keys:

```bash
# From macpro51 to mac-studio
scp ~/.ssh/cluster-keys/macpro51.pub marc@mac-studio:~/.ssh/cluster-keys/

# From mac-studio to macpro51
scp ~/.ssh/cluster-keys/mac-studio.pub marc@macpro51:~/.ssh/cluster-keys/

# Repeat for all node pairs...
```

**Option C: Centralized Distribution**

```bash
# On orchestrator node (mac-studio)
cd ~/.ssh/cluster-keys

# Collect all public keys
for node in macpro51 macbook-air; do
    scp marc@${node}:~/.ssh/cluster-keys/${node}.pub .
done

# Distribute to all nodes
for node in macpro51 macbook-air; do
    scp *.pub marc@${node}:~/.ssh/cluster-keys/
done
```

### 4. Verify Trust

On each node, verify all trusted keys are loaded:

```bash
python3 << 'EOF'
from auth import MessageAuthenticator

auth = MessageAuthenticator("macpro51")  # Use your node ID
print(f"Trusted nodes: {list(auth.public_keys.keys())}")

# Expected: ['macpro51', 'mac-studio', 'macbook-air']
EOF
```

### 5. Test Security

Run the comprehensive test suite:

```bash
cd /mnt/agentic-system/cluster-deployment

# Run all security tests
python3 test_security.py --node-id macpro51 --test-all

# Expected output:
# ALL TESTS PASSED ✓
```

Individual test categories:

```bash
# Test message signing
python3 test_security.py --node-id macpro51 --test-signing

# Test schema validation
python3 test_security.py --test-validation

# Test attack detection
python3 test_security.py --node-id macpro51 --test-attacks
```

## Security Architecture

### Message Flow

```
┌─────────────────┐
│  Source Node    │
│  (macpro51)     │
└────────┬────────┘
         │
         ▼
   [1. Create Task]
         │
         ▼
   [2. Validate Schema]
         │
         ▼
   [3. Sign with Private Key]
         │
         ▼
   [4. Commit to GitHub]
         │
         ▼
    GitHub Repo
         │
         ▼
   [5. Target Node Polls]
         │
         ▼
┌────────┴────────┐
│  Target Node    │
│  (mac-studio)   │
└─────────────────┘
         │
         ▼
   [6. Verify Signature]
         │
         ▼
   [7. Validate Schema]
         │
         ▼
   [8. Execute in Sandbox]
         │
         ▼
   [9. Sign Result]
         │
         ▼
   [10. Post to GitHub]
```

### Trust Model

- **Public Key Infrastructure (PKI)**: Each node has Ed25519 keypair
- **Explicit Trust**: Nodes trust only keys in `~/.ssh/cluster-keys/`
- **Signature Verification**: All messages must be signed by trusted node
- **Message Integrity**: Signatures cover entire payload (JSON canonical form)
- **Non-Repudiation**: Signed messages prove sender identity

### Attack Surface Reduction

| Attack Vector | Previous | Now | Protection |
|---------------|----------|-----|------------|
| Command Injection | ⚠️ Vulnerable (`shell=True`) | ✅ Blocked | Argument lists only |
| Message Forgery | ⚠️ No authentication | ✅ Blocked | Ed25519 signatures |
| Tampering | ⚠️ No integrity checks | ✅ Blocked | Cryptographic signatures |
| Directory Traversal | ⚠️ Unvalidated paths | ✅ Blocked | Schema validation |
| Shell Injection | ⚠️ Arguments unchecked | ✅ Blocked | Dangerous char detection |
| Future Timestamps | ⚠️ Accepted | ✅ Blocked | Timestamp validation |
| Env Var Override | ⚠️ All variables | ✅ Blocked | Protected list (PATH, etc.) |
| Unsigned Messages | ⚠️ Accepted | ✅ Blocked | Signature required |

## Usage Examples

### Creating a Secure Task

```python
from auth import MessageAuthenticator
from payload_schema import TaskPayload, CodeExecutionPayload, TaskType

# Initialize authenticator for source node
auth = MessageAuthenticator(node_id="macpro51")

# Create task payload
task = TaskPayload(
    type=TaskType.CODE_EXECUTION,
    source_node="macpro51",
    target_node="mac-studio",
    payload={
        "code": "print('Hello from secure GitMQ!')",
        "code_language": "python",
        "dependencies": ["requests>=2.31.0"],
        "entry_point": "main.py"
    }
)

# Validate schema
assert task.verify_checksum()

# Sign the task
signed_task = auth.sign_payload(task.model_dump(mode='json'))

# Now commit to GitHub...
```

### Verifying a Received Task

```python
from auth import MessageAuthenticator
from payload_schema import validate_payload, TaskPayload
from pydantic import ValidationError

# Initialize authenticator for target node
auth = MessageAuthenticator(node_id="mac-studio")

# Received task from GitHub
received_task = {...}  # From git commit message

# Step 1: Verify signature
if not auth.verify_payload(received_task.copy()):
    raise SecurityError("Signature verification failed - untrusted source")

# Step 2: Validate schema
try:
    validated_task = validate_payload(received_task, TaskPayload)
except ValidationError as e:
    raise ValueError(f"Invalid task schema: {e}")

# Step 3: Execute safely
# Now safe to execute...
```

## Key Management

### Key Rotation

To rotate a compromised key:

```bash
# 1. Generate new keypair
rm ~/.ssh/cluster-keys/macpro51.priv
rm ~/.ssh/cluster-keys/macpro51.pub
python3 -c "from auth import MessageAuthenticator; MessageAuthenticator('macpro51')"

# 2. Redistribute new public key to all nodes
# (Use Option B or C from setup above)

# 3. Old private key is now invalid (good!)
```

### Revoking a Node

To remove trust from a compromised node:

```bash
# On all healthy nodes, remove the compromised node's public key
rm ~/.ssh/cluster-keys/compromised-node.pub

# Restart daemon to reload keys
# That node can no longer send valid messages
```

### Backup Keys

**DO NOT** store private keys in:
- Git repositories
- Cloud storage
- Unencrypted backups

**DO** store private keys:
- On local disk only (`~/.ssh/cluster-keys/*.priv`)
- With 600 permissions
- Encrypted backup (if needed)

## Troubleshooting

### "No public key found for node: X"

**Cause**: Target node doesn't have sender's public key.

**Fix**:
```bash
# On target node
scp marc@sender-node:~/.ssh/cluster-keys/sender-node.pub ~/.ssh/cluster-keys/
```

### "Signature verification failed"

**Possible causes**:
1. Message tampered with
2. Sender using old/different key
3. Clock skew causing timestamp issues

**Debug**:
```python
from auth import MessageAuthenticator

auth = MessageAuthenticator("your-node")
print(f"Trusted keys: {list(auth.public_keys.keys())}")

# Check if sender is in trusted list
```

### "Schema validation failed"

**Cause**: Payload doesn't match expected schema.

**Debug**:
```python
from payload_schema import TaskPayload, validate_payload
from pydantic import ValidationError

try:
    validate_payload(your_payload, TaskPayload)
except ValidationError as e:
    print(e.errors())
```

### "Shell injection blocked"

**Cause**: Argument contains dangerous characters (`;`, `|`, `&`, etc.)

**Fix**: Remove shell metacharacters from arguments. Use proper argument passing, not shell commands.

**Wrong**:
```python
arguments=["--flag; rm -rf /"]  # ❌ Blocked
```

**Right**:
```python
arguments=["--flag", "value"]  # ✅ Safe
```

## Performance Impact

Security improvements add minimal overhead:

- **Signing**: ~0.1ms per message (Ed25519 is fast)
- **Verification**: ~0.2ms per message
- **Schema Validation**: ~1-2ms per message
- **Sandboxing**: Same as before (filesystem isolation)

**Total overhead**: <5ms per task (negligible for typical execution times)

## Security Checklist

Before deploying to production:

- [ ] All nodes have keypairs generated
- [ ] Public keys distributed to all nodes
- [ ] Trust verified (check `auth.public_keys` on each node)
- [ ] Private keys have 600 permissions
- [ ] Test suite passes on all nodes
- [ ] No `shell=True` in any code
- [ ] All tasks go through `execute_code_secure()`
- [ ] Results are signed before posting
- [ ] Backup keys securely stored (encrypted)
- [ ] Documented incident response for key compromise

## Next Steps

**Immediate (Phase 0 - Complete)**:
- ✅ Remove `shell=True` vulnerability
- ✅ Implement cryptographic signatures
- ✅ Add schema validation
- ✅ Sandbox code execution

**Phase 1: Payload Transport** (Next):
- [ ] Git LFS integration for large files
- [ ] Dependency manager with virtualenv caching
- [ ] Payload compression (Zstandard)

**Phase 2: Memory Synchronization**:
- [ ] Vector clocks for causal ordering
- [ ] CRDT-based memory sync
- [ ] Bloom filters for efficient sync

**Phase 3: Human-in-the-Loop**:
- [ ] Risk scoring engine
- [ ] Arduino approval controller
- [ ] Escalation workflows

See `IMPLEMENTATION_ROADMAP.md` for complete timeline.

## References

- **Ed25519**: https://ed25519.cr.yp.to/
- **Pydantic**: https://docs.pydantic.dev/
- **Command Injection**: https://owasp.org/www-community/attacks/Command_Injection
- **Message Authentication**: https://en.wikipedia.org/wiki/Message_authentication_code

## Support

For security issues or questions:
1. Review this documentation
2. Run `test_security.py` for diagnostics
3. Check logs: `~/agentic-system/logs/github-daemon.log`
4. Review implementation in `auth.py` and `payload_schema.py`

---

**Security is not a feature, it's a requirement.**

Last updated: 2025-11-16
