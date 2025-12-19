#!/usr/bin/env python3
"""
Port Safety Check Hook for Claude Code
Automatically checks and resolves port conflicts before starting services
"""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

# Add port manager to path
sys.path.insert(0, "/home/marc/Documents/Cline/MCP")

# Common service defaults that often conflict
SERVICE_PORT_DEFAULTS = {
    "react": 3000,
    "next": 3000,
    "vue": 3000,
    "vite": 3000,
    "create-react-app": 3000,
    "express": 3000,
    "fastapi": 8000,
    "django": 8000,
    "flask": 5000,
    "rails": 3000,
    "phoenix": 4000,
    "streamlit": 8501,
    "jupyter": 8888,
    "grafana": 3000,
    "prometheus": 9090,
}

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        sock.close()
        return False

def find_next_available_port(start_port: int, max_attempts: int = 100) -> int:
    """Find the next available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if not is_port_in_use(port):
            return port
    return start_port + max_attempts

def suggest_port_for_service(service_type: str, default_port: int) -> int:
    """Suggest an alternative port for a service if the default is busy."""
    if is_port_in_use(default_port):
        # Find alternative based on service type
        if service_type in ["react", "next", "vue", "vite", "frontend"]:
            return find_next_available_port(3001, 99)  # 3001-3099
        elif service_type in ["api", "backend", "fastapi", "django", "flask"]:
            return find_next_available_port(8001, 99)  # 8001-8099
        elif service_type in ["rails", "phoenix"]:
            return find_next_available_port(4001, 99)  # 4001-4099
        else:
            return find_next_available_port(default_port + 1, 100)
    return default_port

def update_package_json_port(project_path: Path, new_port: int):
    """Update the port in package.json scripts."""
    package_json_path = project_path / "package.json"
    if package_json_path.exists():
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        # Update scripts that might use ports
        if "scripts" in package_data:
            for script_name, script_cmd in package_data["scripts"].items():
                if "PORT=" not in script_cmd and any(x in script_cmd for x in ["react-scripts", "next", "vite", "vue-cli-service"]):
                    # Add PORT environment variable
                    package_data["scripts"][script_name] = f"PORT={new_port} {script_cmd}"
                elif "PORT=" in script_cmd:
                    # Update existing PORT
                    import re
                    package_data["scripts"][script_name] = re.sub(r'PORT=\d+', f'PORT={new_port}', script_cmd)
        
        with open(package_json_path, 'w') as f:
            json.dump(package_data, f, indent=2)
        
        return True
    return False

def create_env_file_with_port(project_path: Path, new_port: int):
    """Create or update .env file with PORT configuration."""
    env_path = project_path / ".env"
    env_local_path = project_path / ".env.local"
    
    # Prefer .env.local for Next.js projects
    target_env = env_local_path if (project_path / "next.config.js").exists() else env_path
    
    lines = []
    if target_env.exists():
        with open(target_env, 'r') as f:
            lines = f.readlines()
    
    # Update or add PORT
    port_found = False
    for i, line in enumerate(lines):
        if line.startswith("PORT="):
            lines[i] = f"PORT={new_port}\n"
            port_found = True
            break
    
    if not port_found:
        lines.insert(0, f"PORT={new_port}\n")
    
    with open(target_env, 'w') as f:
        f.writelines(lines)
    
    return True

def check_and_fix_port_conflicts(project_path: Path = None):
    """Main function to check and fix port conflicts."""
    if not project_path:
        project_path = Path.cwd()
    
    # Detect project type
    project_type = "unknown"
    default_port = 3000
    
    if (project_path / "package.json").exists():
        with open(project_path / "package.json", 'r') as f:
            package_data = json.load(f)
            
            # Detect framework
            deps = package_data.get("dependencies", {})
            dev_deps = package_data.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}
            
            if "next" in all_deps:
                project_type = "next"
            elif "react-scripts" in all_deps:
                project_type = "react"
            elif "@vitejs/plugin-react" in all_deps or "vite" in all_deps:
                project_type = "vite"
            elif "@vue/cli-service" in all_deps:
                project_type = "vue"
    elif (project_path / "requirements.txt").exists():
        with open(project_path / "requirements.txt", 'r') as f:
            requirements = f.read().lower()
            if "fastapi" in requirements:
                project_type = "fastapi"
                default_port = 8000
            elif "django" in requirements:
                project_type = "django"
                default_port = 8000
            elif "flask" in requirements:
                project_type = "flask"
                default_port = 5000
            elif "streamlit" in requirements:
                project_type = "streamlit"
                default_port = 8501
    
    # Check if default port is in use
    if is_port_in_use(default_port):
        new_port = suggest_port_for_service(project_type, default_port)
        
        print(f"⚠️  Port {default_port} is already in use!")
        print(f"✅ Automatically configuring {project_type} to use port {new_port}")
        
        # Apply the fix based on project type
        if project_type in ["react", "next", "vue", "vite"]:
            # Update package.json
            if update_package_json_port(project_path, new_port):
                print(f"✅ Updated package.json scripts to use port {new_port}")
            
            # Create/update .env file
            if create_env_file_with_port(project_path, new_port):
                print(f"✅ Updated environment file with PORT={new_port}")
        
        elif project_type in ["fastapi", "django", "flask"]:
            # Create launch script
            launch_script = project_path / "start_with_port.sh"
            with open(launch_script, 'w') as f:
                if project_type == "fastapi":
                    f.write(f"#!/bin/bash\nuvicorn main:app --reload --port {new_port}\n")
                elif project_type == "django":
                    f.write(f"#!/bin/bash\npython manage.py runserver {new_port}\n")
                elif project_type == "flask":
                    f.write(f"#!/bin/bash\nFLASK_RUN_PORT={new_port} flask run\n")
            
            launch_script.chmod(0o755)
            print(f"✅ Created start_with_port.sh to use port {new_port}")
        
        return new_port
    else:
        print(f"✅ Port {default_port} is available for {project_type}")
        return default_port

if __name__ == "__main__":
    # This runs as a hook when services are starting
    port = check_and_fix_port_conflicts()
    
    # Export the port for use by other hooks or scripts
    print(f"export SERVICE_PORT={port}")