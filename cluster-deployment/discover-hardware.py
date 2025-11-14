#!/usr/bin/env python3
"""
Hardware Discovery Script for Agentic Cluster Nodes

Runs on the node to discover and report hardware capabilities
to the cluster orchestrator.
"""

import json
import subprocess
import platform
import psutil
import socket
from pathlib import Path
from datetime import datetime

def get_cpu_info():
    """Discover CPU capabilities"""
    info = {
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'physical_cores': psutil.cpu_count(logical=False),
        'logical_cores': psutil.cpu_count(logical=True),
        'max_frequency_mhz': 0,
        'current_frequency_mhz': 0,
    }

    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            info['max_frequency_mhz'] = cpu_freq.max
            info['current_frequency_mhz'] = cpu_freq.current
    except:
        pass

    # Try to get more detailed CPU info on Linux
    if platform.system() == 'Linux':
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                # Get model name
                for line in cpuinfo.split('\n'):
                    if 'model name' in line:
                        info['model_name'] = line.split(':')[1].strip()
                        break
        except:
            pass

    return info

def get_memory_info():
    """Discover memory capabilities"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        'total_ram_gb': round(mem.total / (1024**3), 2),
        'available_ram_gb': round(mem.available / (1024**3), 2),
        'total_swap_gb': round(swap.total / (1024**3), 2),
        'memory_type': 'unknown',  # Would need dmidecode on Linux
    }

def get_storage_info():
    """Discover storage capabilities"""
    storage = []

    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            device_info = {
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'filesystem': partition.fstype,
                'total_gb': round(usage.total / (1024**3), 2),
                'used_gb': round(usage.used / (1024**3), 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'percent_used': usage.percent,
            }

            # Try to detect SSD vs HDD on Linux
            if platform.system() == 'Linux':
                try:
                    device_name = partition.device.split('/')[-1].rstrip('0123456789')
                    rotational_file = f'/sys/block/{device_name}/queue/rotational'
                    if Path(rotational_file).exists():
                        with open(rotational_file, 'r') as f:
                            device_info['is_ssd'] = f.read().strip() == '0'
                except:
                    pass

            storage.append(device_info)
        except PermissionError:
            continue

    return storage

def get_network_info():
    """Discover network capabilities"""
    networks = []

    for interface, addrs in psutil.net_if_addrs().items():
        if interface == 'lo':
            continue

        net_info = {
            'interface': interface,
            'addresses': []
        }

        for addr in addrs:
            if addr.family == socket.AF_INET:
                net_info['addresses'].append({
                    'type': 'ipv4',
                    'address': addr.address,
                    'netmask': addr.netmask
                })
            elif addr.family == socket.AF_INET6:
                net_info['addresses'].append({
                    'type': 'ipv6',
                    'address': addr.address
                })

        # Get interface stats
        try:
            stats = psutil.net_if_stats()[interface]
            net_info['speed_mbps'] = stats.speed
            net_info['mtu'] = stats.mtu
            net_info['is_up'] = stats.isup
        except:
            pass

        if net_info['addresses']:
            networks.append(net_info)

    return networks

def get_gpu_info():
    """Discover GPU capabilities (if any)"""
    gpus = []

    # Try lspci on Linux
    if platform.system() == 'Linux':
        try:
            result = subprocess.run(
                ['lspci', '-v'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                current_gpu = None
                for line in result.stdout.split('\n'):
                    if 'VGA compatible controller' in line or '3D controller' in line:
                        current_gpu = {
                            'type': 'VGA' if 'VGA' in line else '3D',
                            'description': line.split('controller:')[1].strip() if 'controller:' in line else 'Unknown'
                        }
                        gpus.append(current_gpu)
        except:
            pass

    return gpus if gpus else [{'type': 'none', 'description': 'No GPU detected'}]

def get_container_runtime():
    """Check available container runtimes"""
    runtimes = []

    for runtime in ['docker', 'podman', 'buildah']:
        try:
            result = subprocess.run(
                [runtime, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                runtimes.append({
                    'name': runtime,
                    'version': result.stdout.strip().split('\n')[0]
                })
        except:
            pass

    return runtimes

def get_build_tools():
    """Check available build tools"""
    tools = []

    build_commands = {
        'cmake': ['cmake', '--version'],
        'make': ['make', '--version'],
        'gcc': ['gcc', '--version'],
        'g++': ['g++', '--version'],
        'clang': ['clang', '--version'],
        'python3': ['python3', '--version'],
        'node': ['node', '--version'],
        'npm': ['npm', '--version'],
        'cargo': ['cargo', '--version'],
        'go': ['go', 'version'],
    }

    for tool, command in build_commands.items():
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                tools.append({
                    'name': tool,
                    'version': result.stdout.strip().split('\n')[0]
                })
        except:
            pass

    return tools

def calculate_performance_score():
    """Calculate relative performance score"""
    # Simple scoring based on hardware
    cpu = psutil.cpu_count(logical=False) or 1
    ram_gb = psutil.virtual_memory().total / (1024**3)

    # Score formula (arbitrary but relative)
    score = (cpu * 10) + (ram_gb * 2)

    return round(score, 1)

def discover_all():
    """Run complete hardware discovery"""

    discovery = {
        'timestamp': datetime.now().isoformat(),
        'hostname': socket.gethostname(),
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
        },
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'storage': get_storage_info(),
        'network': get_network_info(),
        'gpu': get_gpu_info(),
        'container_runtimes': get_container_runtime(),
        'build_tools': get_build_tools(),
        'performance_score': calculate_performance_score(),
    }

    return discovery

def save_discovery(node_id, discovery_data):
    """Save discovery data to cluster"""

    # Try to save to cluster if mounted
    cluster_path = Path('/mnt/ssdraid0/agentic-system/databases/cluster/nodes') / node_id / 'hardware_profile.json'
    local_path = Path.home() / '.local/share/agentic-system' / 'hardware_profile.json'

    # Ensure local directory exists
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Save locally
    with open(local_path, 'w') as f:
        json.dump(discovery_data, f, indent=2)
    print(f"✅ Hardware profile saved locally: {local_path}")

    # Try to save to cluster
    if cluster_path.parent.exists():
        with open(cluster_path, 'w') as f:
            json.dump(discovery_data, f, indent=2)
        print(f"✅ Hardware profile saved to cluster: {cluster_path}")
        return cluster_path
    else:
        print(f"⚠️  Cluster path not available: {cluster_path.parent}")
        print("   Profile saved locally only - will sync when cluster is mounted")
        return local_path

def print_summary(discovery_data):
    """Print human-readable summary"""
    print("\n" + "="*60)
    print("Hardware Discovery Summary")
    print("="*60)

    cpu = discovery_data['cpu']
    mem = discovery_data['memory']

    print(f"\n🖥️  System: {discovery_data['platform']['system']} {discovery_data['platform']['release']}")
    print(f"   Hostname: {discovery_data['hostname']}")

    print(f"\n⚙️  CPU:")
    print(f"   Model: {cpu.get('model_name', cpu.get('processor', 'Unknown'))}")
    print(f"   Cores: {cpu['physical_cores']} physical, {cpu['logical_cores']} logical")
    if cpu['max_frequency_mhz']:
        print(f"   Frequency: {cpu['max_frequency_mhz']:.0f} MHz (max)")

    print(f"\n💾 Memory:")
    print(f"   RAM: {mem['total_ram_gb']:.1f} GB total, {mem['available_ram_gb']:.1f} GB available")
    if mem['total_swap_gb']:
        print(f"   Swap: {mem['total_swap_gb']:.1f} GB")

    print(f"\n💿 Storage:")
    for storage in discovery_data['storage']:
        ssd_marker = '⚡ SSD' if storage.get('is_ssd') else '🔄 HDD'
        print(f"   {storage['mountpoint']}: {storage['free_gb']:.1f} GB free / {storage['total_gb']:.1f} GB total {ssd_marker}")

    print(f"\n🌐 Network:")
    for net in discovery_data['network']:
        for addr in net['addresses']:
            if addr['type'] == 'ipv4':
                speed = f" ({net.get('speed_mbps', 0)} Mbps)" if 'speed_mbps' in net else ""
                print(f"   {net['interface']}: {addr['address']}{speed}")

    if discovery_data['gpu'] and discovery_data['gpu'][0]['type'] != 'none':
        print(f"\n🎮 GPU:")
        for gpu in discovery_data['gpu']:
            print(f"   {gpu['description']}")

    if discovery_data['container_runtimes']:
        print(f"\n📦 Container Runtimes:")
        for runtime in discovery_data['container_runtimes']:
            print(f"   {runtime['name']}: {runtime['version']}")

    if discovery_data['build_tools']:
        print(f"\n🔧 Build Tools:")
        for tool in discovery_data['build_tools'][:5]:  # Show first 5
            print(f"   {tool['name']}: {tool['version']}")
        if len(discovery_data['build_tools']) > 5:
            print(f"   ... and {len(discovery_data['build_tools']) - 5} more")

    print(f"\n📊 Performance Score: {discovery_data['performance_score']}")
    print("\n" + "="*60)

if __name__ == '__main__':
    import sys

    # Get node ID from argument or config
    node_id = sys.argv[1] if len(sys.argv) > 1 else 'unknown'

    if node_id == 'unknown':
        # Try to load from config
        config_path = Path.home() / '.claude' / 'node-config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                node_id = config.get('node_id', 'unknown')

    print(f"🔍 Discovering hardware for node: {node_id}")
    print("   This may take a few seconds...")

    # Run discovery
    discovery_data = discover_all()

    # Print summary
    print_summary(discovery_data)

    # Save to disk
    saved_path = save_discovery(node_id, discovery_data)

    print(f"\n✅ Hardware discovery complete!")
    print(f"   Profile saved: {saved_path}")
    print(f"   Orchestrator can now optimize task assignment based on capabilities")
