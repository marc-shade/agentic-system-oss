#!/bin/bash
# BPI-M2 Berry Sentinel Node Setup Script
# Sets up the always-on cluster coordinator and memory guardian

set -e

echo "=========================================="
echo "BPI-M2 Berry Sentinel Node Setup"
echo "=========================================="
echo

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running on correct architecture
check_architecture() {
    info "Checking architecture..."
    ARCH=$(uname -m)
    if [[ "$ARCH" != "armv7l" ]]; then
        warn "Expected armv7l, found $ARCH"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Architecture correct: $ARCH"
    fi
}

# Check if running as correct user
check_user() {
    info "Checking user..."
    if [[ "$USER" != "marc" ]]; then
        warn "Expected user 'marc', found '$USER'"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "User correct: $USER"
    fi
}

# Update system packages
update_system() {
    info "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    success "System updated"
}

# Install required packages
install_packages() {
    info "Installing required packages..."

    PACKAGES=(
        # Core utilities
        python3
        python3-pip
        python3-venv
        sqlite3
        git
        curl
        wget
        rsync

        # Network utilities
        avahi-daemon
        avahi-utils
        dnsutils
        net-tools
        iputils-ping
        openssh-server

        # GPIO libraries
        python3-dev
        python3-gpiod

        # System monitoring
        htop
        iotop
        nethogs
        sysstat

        # Build tools (for Python packages)
        build-essential
        gcc
        make
    )

    sudo apt install -y "${PACKAGES[@]}"
    success "Packages installed"
}

# Create directory structure
create_directories() {
    info "Creating directory structure..."

    AGENTIC_ROOT="$HOME/agentic-system"

    mkdir -p "$AGENTIC_ROOT"/{databases,logs,scripts,services,cluster-deployment}
    mkdir -p "$AGENTIC_ROOT/databases/cluster"
    mkdir -p "$AGENTIC_ROOT/databases/cluster/nodes/bpi-sentinel"
    mkdir -p "/mnt/sentinel-data/cluster-backup"
    mkdir -p "$HOME/.claude"

    success "Directories created"
}

# Setup SSH keys for cluster mesh
setup_ssh_keys() {
    info "Setting up SSH keys..."

    if [[ ! -f "$HOME/.ssh/id_ed25519" ]]; then
        ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" -C "bpi-sentinel@agentic-cluster"
        success "SSH key generated"
    else
        info "SSH key already exists"
    fi

    # Show public key for adding to other nodes
    echo
    warn "Add this public key to other cluster nodes:"
    cat "$HOME/.ssh/id_ed25519.pub"
    echo
    read -p "Press enter when you've added the key to other nodes..."
}

# Clone or update agentic-system repository
setup_repository() {
    info "Setting up agentic-system repository..."

    AGENTIC_ROOT="$HOME/agentic-system"

    if [[ -d "$AGENTIC_ROOT/.git" ]]; then
        info "Repository already exists, pulling updates..."
        cd "$AGENTIC_ROOT"
        git pull
    else
        warn "Please manually copy files from another node or clone the repository"
        warn "Use: rsync -avz mac-studio.local:~/agentic-system/ $AGENTIC_ROOT/"
        read -p "Press enter when repository is ready..."
    fi

    success "Repository ready"
}

# Install Python dependencies
install_python_deps() {
    info "Installing Python dependencies..."

    AGENTIC_ROOT="$HOME/agentic-system"

    # Create virtual environment (optional but recommended)
    # python3 -m venv "$AGENTIC_ROOT/venv"
    # source "$AGENTIC_ROOT/venv/bin/activate"

    # Install common dependencies
    pip3 install --user requests sqlite3 hashlib

    # Install GPIO library
    pip3 install --user gpiod

    success "Python dependencies installed"
}

# Configure node identity
configure_node() {
    info "Configuring node identity..."

    cat > "$HOME/.claude/node-config.toon" <<EOF
# BPI-M2 Berry Sentinel Node
node_id: bpi-sentinel
hostname: bpi-sentinel.local
role: sentinel
architecture: armv7l

cluster:
  peer_nodes:
    - node_id: macpro51, ip: 192.168.1.77, role: builder, arch: x86_64
    - node_id: mac-studio, ip: 192.168.1.16, role: orchestrator, arch: arm64
    - node_id: macbook-air, ip: 192.168.1.76, role: researcher, arch: arm64
EOF

    success "Node configuration created"
}

# Set hostname
set_hostname() {
    info "Setting hostname to bpi-sentinel..."

    sudo hostnamectl set-hostname bpi-sentinel

    # Update /etc/hosts
    sudo sed -i "s/127.0.1.1.*/127.0.1.1\tbpi-sentinel.local bpi-sentinel/" /etc/hosts

    success "Hostname set to bpi-sentinel"
}

# Configure Avahi/mDNS
configure_avahi() {
    info "Configuring Avahi/mDNS service discovery..."

    sudo systemctl enable avahi-daemon
    sudo systemctl start avahi-daemon

    # Create service file for sentinel
    sudo tee /etc/avahi/services/agentic-sentinel.service >/dev/null <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Agentic Sentinel on %h</name>
  <service>
    <type>_agentic-sentinel._tcp</type>
    <port>9100</port>
    <txt-record>role=sentinel</txt-record>
    <txt-record>arch=armv7l</txt-record>
    <txt-record>node_id=bpi-sentinel</txt-record>
  </service>
</service-group>
EOF

    sudo systemctl restart avahi-daemon
    success "Avahi configured"
}

# Install systemd services
install_services() {
    info "Installing systemd services..."

    AGENTIC_ROOT="$HOME/agentic-system"

    # Make scripts executable
    chmod +x "$AGENTIC_ROOT/services/cluster-sentinel.py"
    chmod +x "$AGENTIC_ROOT/services/memory-replication.py"

    # Copy service files to systemd
    sudo cp "$AGENTIC_ROOT/services/systemd/cluster-sentinel.service" /etc/systemd/system/
    sudo cp "$AGENTIC_ROOT/services/systemd/memory-replication.service" /etc/systemd/system/
    sudo cp "$AGENTIC_ROOT/services/systemd/agentic-cluster.target" /etc/systemd/system/

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable services (but don't start yet)
    sudo systemctl enable cluster-sentinel.service
    sudo systemctl enable memory-replication.service
    sudo systemctl enable agentic-cluster.target

    success "Services installed and enabled"
}

# Configure firewall
configure_firewall() {
    info "Configuring firewall..."

    # Check if ufw is installed
    if command -v ufw &> /dev/null; then
        sudo ufw allow from 192.168.1.0/24 to any port 22 comment 'SSH from cluster'
        sudo ufw allow from 192.168.1.0/24 to any port 9100 comment 'Sentinel API'
        sudo ufw allow from 192.168.1.0/24 to any port 9101 comment 'Sentinel metrics'
        sudo ufw allow from 192.168.1.0/24 to any port 5353 comment 'mDNS'

        # Enable if not already
        sudo ufw --force enable
        success "Firewall configured"
    else
        warn "UFW not installed, skipping firewall configuration"
    fi
}

# Test cluster connectivity
test_connectivity() {
    info "Testing cluster connectivity..."

    NODES=(
        "192.168.1.77:macpro51"
        "192.168.1.16:mac-studio"
        "192.168.1.76:macbook-air"
    )

    for node in "${NODES[@]}"; do
        IP="${node%%:*}"
        NAME="${node##*:}"

        if ping -c 1 -W 2 "$IP" &>/dev/null; then
            success "✓ $NAME ($IP) reachable"
        else
            warn "✗ $NAME ($IP) unreachable"
        fi

        if ssh -o ConnectTimeout=3 -o BatchMode=yes "$IP" "echo ok" &>/dev/null; then
            success "✓ $NAME ($IP) SSH accessible"
        else
            warn "✗ $NAME ($IP) SSH not accessible (add public key?)"
        fi
    done
}

# Mount SATA drive for backups
mount_sata_drive() {
    info "Checking SATA drive for backups..."

    # Check if SATA drive exists
    if lsblk | grep -q sda; then
        info "SATA drive detected"

        # Check if already mounted
        if mountpoint -q /mnt/sentinel-data; then
            success "SATA drive already mounted at /mnt/sentinel-data"
        else
            warn "SATA drive not mounted"
            info "To mount: sudo mount /dev/sda1 /mnt/sentinel-data"
            info "To auto-mount on boot, add to /etc/fstab"
        fi
    else
        warn "No SATA drive detected"
        info "Will use local storage for backups"
        mkdir -p "$HOME/sentinel-data/cluster-backup"
    fi
}

# Final configuration check
final_check() {
    info "Running final configuration check..."

    CHECKS=(
        "$HOME/agentic-system:Agentic system directory"
        "$HOME/.claude/node-config.toon:Node configuration"
        "$HOME/.ssh/id_ed25519:SSH key"
        "/etc/systemd/system/cluster-sentinel.service:Sentinel service"
        "/etc/systemd/system/memory-replication.service:Replication service"
    )

    ALL_OK=true
    for check in "${CHECKS[@]}"; do
        PATH="${check%%:*}"
        DESC="${check##*:}"

        if [[ -e "$PATH" ]]; then
            success "✓ $DESC"
        else
            error "✗ $DESC missing"
            ALL_OK=false
        fi
    done

    if $ALL_OK; then
        success "All checks passed!"
    else
        error "Some checks failed"
        return 1
    fi
}

# Print next steps
print_next_steps() {
    echo
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo
    echo "1. Verify cluster connectivity:"
    echo "   for ip in 192.168.1.77 192.168.1.16 192.168.1.76; do ssh \$ip hostname; done"
    echo
    echo "2. Initialize cluster databases:"
    echo "   cd ~/agentic-system/cluster-deployment"
    echo "   python3 init_cluster_db.py"
    echo
    echo "3. Start sentinel services:"
    echo "   sudo systemctl start agentic-cluster.target"
    echo "   sudo systemctl status cluster-sentinel.service"
    echo "   sudo systemctl status memory-replication.service"
    echo
    echo "4. Monitor logs:"
    echo "   sudo journalctl -u cluster-sentinel.service -f"
    echo "   sudo journalctl -u memory-replication.service -f"
    echo
    echo "5. Test sentinel functionality:"
    echo "   python3 ~/agentic-system/services/cluster-sentinel.py  # Run once manually"
    echo
    echo "6. Set up environmental monitoring (optional):"
    echo "   See: ~/agentic-system/services/environmental-monitor.py"
    echo
    echo "=========================================="
}

# Main setup flow
main() {
    check_architecture
    check_user

    info "Starting BPI-M2 Berry Sentinel setup..."
    echo

    update_system
    install_packages
    create_directories
    set_hostname
    configure_avahi
    setup_ssh_keys
    setup_repository
    install_python_deps
    configure_node
    mount_sata_drive
    install_services
    configure_firewall
    test_connectivity
    final_check

    print_next_steps
}

# Run main
main
