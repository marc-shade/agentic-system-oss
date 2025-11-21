# Installing Apple Container Runtime

## Quick Install Instructions

The Apple Container installer has been downloaded to:
```
/tmp/container-0.6.0-installer-signed.pkg
```

**To install, run:**
```bash
sudo installer -pkg /tmp/container-0.6.0-installer-signed.pkg -target /
```

This will install Apple Container to `/usr/local`.

**After installation, start the service:**
```bash
container system start
```

**Verify installation:**
```bash
container --version
```

## What is Apple Container?

Apple Container is a Swift-based container runtime optimized for Apple silicon that:
- Runs Linux containers as lightweight VMs
- Is OCI-compatible (works with Docker images)
- Integrates with standard container registries
- Uses native macOS virtualization

## System Requirements

- ✅ Mac with Apple silicon
- ✅ macOS 26 or later (you have macOS 26.1)

## Basic Usage

```bash
# Start the service
container system start

# Pull an image
container pull alpine:latest

# Run a container
container run alpine:latest echo "Hello World"

# List containers
container ps

# Stop the service
container system stop
```

## Integration with AGI System

Once installed, the sandboxed testing environment will automatically detect and use Apple Container for:
- Isolated test execution
- Performance benchmarking
- Security validation
- Safe deployment testing

## Why Apple Container?

1. **Native Performance**: Optimized for Apple silicon
2. **OCI Compatible**: Works with standard Docker images
3. **Lightweight**: Uses macOS virtualization framework
4. **Secure**: Proper isolation for testing self-modifications

---

**Ready to proceed once installed!** I'll integrate it into the sandboxed testing environment.
