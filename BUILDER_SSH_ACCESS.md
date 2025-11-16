# Builder Node SSH Access Configuration

**Node**: macpro51 (Builder)
**IP Address**: 192.168.1.183
**Hostname**: macpro51.local
**User**: marc
**Date**: 2025-11-14

---

## SSH Server Status

- **Service**: sshd.service (active, running)
- **Port**: 22 (default)
- **Auto-start**: Enabled on boot
- **Protocol**: SSH-2

---

## Builder Node Public SSH Key

**For Orchestrator to Add to Its ~/.ssh/authorized_keys**:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJWAInJDC4Jy8UfXvkCnEf/x1Gt/BPCT6He9URVXLUbb marc@macpro51-builder
```

**Key Type**: ED25519 (modern, secure, fast)
**Fingerprint**: SHA256:pMhmHUUaGjP0AHe/K0Iqo57ve3NpdLHXhFlk1tR4FnY

---

## Orchestrator SSH Access to Builder

**From mac-studio (192.168.1.16)**, the orchestrator needs to:

### 1. Add Builder's Public Key to Orchestrator's authorized_keys

On **mac-studio**:
```bash
# Add Builder's public key to allow Builder to SSH to orchestrator
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJWAInJDC4Jy8UfXvkCnEf/x1Gt/BPCT6He9URVXLUbb marc@macpro51-builder" >> ~/.ssh/authorized_keys
```

### 2. Get Orchestrator's Public Key

On **mac-studio**:
```bash
# If no SSH key exists, generate one:
ssh-keygen -t ed25519 -C "marc@mac-studio-orchestrator" -f ~/.ssh/id_ed25519

# Display public key to add to Builder:
cat ~/.ssh/id_ed25519.pub
```

### 3. Add Orchestrator's Public Key to Builder

The orchestrator's public key needs to be added to Builder's `~/.ssh/authorized_keys`.

**On Builder (macpro51)**, add the orchestrator's public key:
```bash
# Add orchestrator's public key (replace with actual key from mac-studio):
echo "<orchestrator-public-key-here>" >> ~/.ssh/authorized_keys
```

Or use **telnet** to add it remotely:
```bash
# From mac-studio, telnet to Builder:
telnet macpro51.local 9999

# Once logged in, add the key:
echo "<your-mac-studio-public-key>" >> ~/.ssh/authorized_keys
exit
```

---

## Testing SSH Connections

### From Orchestrator to Builder

On **mac-studio**:
```bash
# Test SSH connection
ssh marc@macpro51.local
# or
ssh marc@192.168.1.183

# Add to known_hosts on first connection
# Should connect without password
```

### From Builder to Orchestrator

On **Builder (macpro51)**:
```bash
# Test SSH connection
ssh marc@marcs-mac-studio.local
# or
ssh marc@192.168.1.16

# Should connect without password
```

---

## SSH Configuration

### Builder SSH Config (~/.ssh/config)

Create on **macpro51**:
```bash
cat > ~/.ssh/config << 'EOF'
# Orchestrator (mac-studio)
Host orchestrator mac-studio
    HostName 192.168.1.16
    User marc
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Cluster node aliases
Host macbook-air researcher
    HostName macbook-air.local
    User marc
    IdentityFile ~/.ssh/id_ed25519

Host macbook-pro developer
    HostName macbook-pro.local
    User marc
    IdentityFile ~/.ssh/id_ed25519
EOF

chmod 600 ~/.ssh/config
```

### Orchestrator SSH Config

On **mac-studio**, add Builder:
```bash
cat >> ~/.ssh/config << 'EOF'

# Builder (macpro51)
Host builder macpro51
    HostName 192.168.1.183
    User marc
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
```

---

## Firewall Configuration

SSH is already allowed on the Builder node:

```bash
# Verify SSH is allowed
sudo firewall-cmd --list-services | grep ssh
> ssh

# If needed, add SSH:
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

---

## Security Best Practices

1. **Key-based authentication only** (no passwords)
   - Edit `/etc/ssh/sshd_config`:
   ```
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

2. **Restrict SSH to cluster network**:
   ```bash
   sudo firewall-cmd --permanent --remove-service=ssh
   sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" service name="ssh" accept'
   sudo firewall-cmd --reload
   ```

3. **Use SSH agent forwarding** for multi-hop connections:
   ```bash
   ssh -A marc@macpro51.local
   ```

---

## Troubleshooting

### SSH Connection Refused

1. **Check SSH server**:
   ```bash
   sudo systemctl status sshd
   sudo systemctl restart sshd
   ```

2. **Check firewall**:
   ```bash
   sudo firewall-cmd --list-all | grep ssh
   ```

3. **Check SELinux**:
   ```bash
   sudo ausearch -m avc -ts recent | grep ssh
   ```

### Permission Denied (publickey)

1. **Check key permissions**:
   ```bash
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/id_ed25519
   chmod 644 ~/.ssh/id_ed25519.pub
   ```

2. **Verify key in authorized_keys**:
   ```bash
   cat ~/.ssh/authorized_keys
   ```

3. **Check SSH logs**:
   ```bash
   sudo journalctl -u sshd -f
   ```

### Use Telnet for Emergency Access

If SSH is broken, use telnet:
```bash
# From mac-studio:
telnet macpro51.local 9999

# Fix SSH configuration
sudo systemctl restart sshd
```

---

## Quick Reference

**Builder Node**:
- IP: `192.168.1.183`
- Hostname: `macpro51.local`
- User: `marc`
- Public Key Location: `~/.ssh/id_ed25519.pub`
- Authorized Keys: `~/.ssh/authorized_keys`

**Orchestrator Node**:
- IP: `192.168.1.16`
- Hostname: `marcs-mac-studio.local`
- User: `marc`
- Needs to add: Builder's public key to its authorized_keys
- Needs to provide: Its public key for Builder's authorized_keys

**Emergency Access**:
- Telnet: `telnet macpro51.local 9999`
- Port: 9999 (cluster telnet service)

---

## Next Steps for Full Bidirectional SSH

1. **On mac-studio (Orchestrator)**:
   - Generate SSH key if not exists: `ssh-keygen -t ed25519`
   - Get public key: `cat ~/.ssh/id_ed25519.pub`
   - Add Builder's key to authorized_keys (see above)

2. **On macpro51 (Builder)**:
   - Add orchestrator's public key to `~/.ssh/authorized_keys`

3. **Test connections**:
   - From orchestrator: `ssh marc@macpro51.local`
   - From Builder: `ssh marc@marcs-mac-studio.local`

4. **Verify passwordless access works both ways**

---

**Status**: Builder SSH server ready. Waiting for orchestrator's public key to complete bidirectional access.
