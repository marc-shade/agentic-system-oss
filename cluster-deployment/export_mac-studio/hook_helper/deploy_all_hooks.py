#!/usr/bin/env python3
"""
Comprehensive Hook Deployment System
Safely deploys all hooks to Claude Code settings with backup and rollback capability
"""

import json
import os
import sys
import shutil
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add claude path for imports
sys.path.append('/Users/marc/.claude')

class HookDeploymentManager:
    def __init__(self):
        self.claude_config_path = Path.home() / '.config' / 'claude-desktop' / 'config.json'
        self.hooks_base = Path('/Users/marc/.claude/hooks')
        self.master_config_path = self.hooks_base / 'master_hooks_config.json'
        self.backup_path = self.claude_config_path.with_suffix('.json.backup')
        self.deployment_log = []
        
    def deploy_hooks_system(self) -> Dict[str, Any]:
        """Deploy the complete hooks system to Claude Code"""
        print("🚀 Starting Hook System Deployment...")
        
        try:
            # Step 1: Validate prerequisites
            self.validate_prerequisites()
            
            # Step 2: Create backup
            self.create_backup()
            
            # Step 3: Load configurations
            master_config = self.load_master_config()
            current_config = self.load_current_config()
            
            # Step 4: Merge configurations
            merged_config = self.merge_configurations(current_config, master_config)
            
            # Step 5: Validate merged configuration
            self.validate_merged_config(merged_config)
            
            # Step 6: Deploy configuration
            self.deploy_configuration(merged_config)
            
            # Step 7: Test deployment
            test_results = self.test_deployment()
            
            # Step 8: Generate deployment report
            return self.generate_deployment_report(test_results)
            
        except Exception as e:
            self.log_error(f"Deployment failed: {e}")
            self.rollback_deployment()
            raise
    
    def validate_prerequisites(self):
        """Validate all prerequisites for deployment"""
        print("✅ Validating Prerequisites...")
        
        # Check master config exists
        if not self.master_config_path.exists():
            raise FileNotFoundError(f"Master config not found: {self.master_config_path}")
        
        # Check Claude config directory exists
        self.claude_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate all hook files exist
        with open(self.master_config_path, 'r') as f:
            master_config = json.load(f)
        
        required_files = master_config.get('validation', {}).get('required_files', [])
        missing_files = []
        
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise FileNotFoundError(f"Missing hook files: {missing_files}")
        
        # Make all hook files executable
        self.make_hooks_executable()
        
        # Test Python imports
        self.test_python_imports()
        
        self.log_info("✅ All prerequisites validated")
    
    def make_hooks_executable(self):
        """Make all hook files executable"""
        hook_dirs = ['security', 'quality', 'performance', 'ux']
        
        for hook_dir in hook_dirs:
            dir_path = self.hooks_base / hook_dir
            if dir_path.exists():
                for py_file in dir_path.glob('*.py'):
                    py_file.chmod(0o755)
                    self.log_info(f"Made executable: {py_file}")
    
    def test_python_imports(self):
        """Test that critical Python modules can be imported"""
        critical_modules = [
            '/Users/marc/.claude/principle_0_orchestrator_hook.py',
            '/Users/marc/.claude/enhanced_delegation_enforcement.py',
            '/Users/marc/.claude/siobhan_voice.py'
        ]
        
        for module_path in critical_modules:
            if Path(module_path).exists():
                try:
                    # Test basic import capability
                    result = subprocess.run([
                        'python3', '-c', f'import sys; sys.path.append("{Path(module_path).parent}"); '
                        f'import {Path(module_path).stem}; print("✓ Import OK")'
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode != 0:
                        self.log_warning(f"Import test failed for {module_path}: {result.stderr}")
                except Exception as e:
                    self.log_warning(f"Could not test import for {module_path}: {e}")
    
    def create_backup(self):
        """Create backup of current Claude Code configuration"""
        print("💾 Creating Configuration Backup...")
        
        if self.claude_config_path.exists():
            # Create timestamped backup
            timestamp = int(time.time())
            timestamped_backup = self.claude_config_path.with_suffix(f'.json.backup.{timestamp}')
            shutil.copy2(self.claude_config_path, timestamped_backup)
            
            # Create standard backup for rollback
            shutil.copy2(self.claude_config_path, self.backup_path)
            
            self.log_info(f"✅ Backup created: {timestamped_backup}")
            self.log_info(f"✅ Rollback backup: {self.backup_path}")
        else:
            self.log_info("📝 No existing configuration - creating new configuration")
    
    def load_master_config(self) -> Dict[str, Any]:
        """Load master hooks configuration"""
        with open(self.master_config_path, 'r') as f:
            return json.load(f)
    
    def load_current_config(self) -> Dict[str, Any]:
        """Load current Claude Code configuration"""
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.log_warning(f"Invalid JSON in current config: {e}")
                return {}
        return {}
    
    def merge_configurations(self, current_config: Dict[str, Any], master_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge current configuration with master hooks configuration"""
        print("🔄 Merging Configurations...")
        
        # Start with current config
        merged = current_config.copy()
        
        # Extract hooks from master config
        hooks_config = master_config.get('hooks', {})
        
        # Merge hooks into current config
        if 'hooks' not in merged:
            merged['hooks'] = {}
        
        # Merge each hook type
        for hook_type, hook_configs in hooks_config.items():
            if hook_type not in merged['hooks']:
                merged['hooks'][hook_type] = []
            
            # Add new hooks (avoid duplicates by checking commands)
            existing_commands = set()
            for existing_hook in merged['hooks'][hook_type]:
                if isinstance(existing_hook, dict) and 'hooks' in existing_hook:
                    for hook in existing_hook['hooks']:
                        if 'command' in hook:
                            existing_commands.add(hook['command'])
            
            # Add new hook configurations
            for hook_config in hook_configs:
                if isinstance(hook_config, dict) and 'hooks' in hook_config:
                    # Filter out duplicate commands
                    new_hooks = []
                    for hook in hook_config['hooks']:
                        if 'command' in hook and hook['command'] not in existing_commands:
                            new_hooks.append(hook)
                            existing_commands.add(hook['command'])
                    
                    if new_hooks:
                        new_config = hook_config.copy()
                        new_config['hooks'] = new_hooks
                        merged['hooks'][hook_type].append(new_config)
        
        self.log_info("✅ Configurations merged successfully")
        return merged
    
    def validate_merged_config(self, config: Dict[str, Any]):
        """Validate the merged configuration"""
        print("🔍 Validating Merged Configuration...")
        
        # Check JSON structure
        try:
            json.dumps(config)
        except Exception as e:
            raise ValueError(f"Invalid JSON structure: {e}")
        
        # Check hooks structure
        if 'hooks' in config:
            hooks = config['hooks']
            if not isinstance(hooks, dict):
                raise ValueError("Hooks section must be a dictionary")
            
            # Validate each hook type
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    raise ValueError(f"Hook type '{hook_type}' must be a list")
                
                for hook_config in hook_list:
                    if not isinstance(hook_config, dict):
                        raise ValueError(f"Hook config in '{hook_type}' must be a dictionary")
                    
                    if 'hooks' in hook_config:
                        for hook in hook_config['hooks']:
                            if 'command' not in hook:
                                raise ValueError(f"Hook missing 'command' field in '{hook_type}'")
        
        self.log_info("✅ Configuration validation passed")
    
    def deploy_configuration(self, config: Dict[str, Any]):
        """Deploy the merged configuration to Claude Code"""
        print("🚀 Deploying Configuration...")
        
        # Write configuration to Claude Code config file
        with open(self.claude_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.log_info(f"✅ Configuration deployed to: {self.claude_config_path}")
        
        # Set appropriate permissions
        self.claude_config_path.chmod(0o644)
    
    def test_deployment(self) -> Dict[str, Any]:
        """Test the deployed hooks system"""
        print("🧪 Testing Deployed Hooks...")
        
        # Run integration test suite
        test_script = self.hooks_base / 'test_all_hooks_integration.py'
        test_results = {}
        
        if test_script.exists():
            try:
                result = subprocess.run([
                    'python3', str(test_script)
                ], capture_output=True, text=True, timeout=120)
                
                test_results = {
                    'test_script_run': True,
                    'return_code': result.returncode,
                    'output': result.stdout,
                    'errors': result.stderr,
                    'success': result.returncode == 0
                }
                
                if result.returncode == 0:
                    self.log_info("✅ Hook integration tests passed")
                else:
                    self.log_warning(f"⚠️ Some hook tests failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                test_results = {
                    'test_script_run': False,
                    'error': 'Test script timeout',
                    'success': False
                }
                self.log_warning("⚠️ Hook integration tests timed out")
            except Exception as e:
                test_results = {
                    'test_script_run': False,
                    'error': str(e),
                    'success': False
                }
                self.log_warning(f"⚠️ Could not run hook integration tests: {e}")
        else:
            test_results = {
                'test_script_run': False,
                'error': 'Test script not found',
                'success': False
            }
            self.log_warning("⚠️ Hook integration test script not found")
        
        # Test basic configuration loading
        try:
            with open(self.claude_config_path, 'r') as f:
                loaded_config = json.load(f)
            test_results['config_loadable'] = True
            test_results['hooks_count'] = sum(len(hooks) for hooks in loaded_config.get('hooks', {}).values())
        except Exception as e:
            test_results['config_loadable'] = False
            test_results['config_error'] = str(e)
        
        return test_results
    
    def rollback_deployment(self):
        """Rollback to previous configuration"""
        print("🔙 Rolling Back Deployment...")
        
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.claude_config_path)
            self.log_info(f"✅ Rolled back to: {self.backup_path}")
        else:
            self.log_warning("⚠️ No backup found for rollback")
    
    def generate_deployment_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive deployment report"""
        print("📊 Generating Deployment Report...")
        
        deployment_time = time.time()
        
        report = {
            'deployment_summary': {
                'timestamp': deployment_time,
                'success': test_results.get('success', False),
                'configuration_path': str(self.claude_config_path),
                'backup_path': str(self.backup_path),
                'hooks_deployed': test_results.get('hooks_count', 0)
            },
            'test_results': test_results,
            'deployment_log': self.deployment_log,
            'hook_categories': {
                'security': 4,
                'quality': 4,
                'performance': 5,
                'ux': 6
            },
            'next_steps': [
                "Restart Claude Code to activate hooks",
                "Monitor hook performance in first session",
                "Check logs for any issues: /Users/marc/.claude/logs/",
                "Run manual validation: python3 /Users/marc/.claude/hooks/test_all_hooks_integration.py"
            ]
        }
        
        # Save report
        report_path = self.hooks_base / 'deployment_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_info(f"📊 Deployment report saved: {report_path}")
        
        # Print summary
        print(f"\n🎯 DEPLOYMENT SUMMARY:")
        print(f"   Status: {'✅ SUCCESS' if report['deployment_summary']['success'] else '❌ PARTIAL'}")
        print(f"   Hooks Deployed: {report['deployment_summary']['hooks_deployed']}")
        print(f"   Config Path: {report['deployment_summary']['configuration_path']}")
        print(f"   Backup Path: {report['deployment_summary']['backup_path']}")
        
        return report
    
    def log_info(self, message: str):
        """Log info message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] INFO: {message}"
        self.deployment_log.append(log_entry)
        print(f"ℹ️ {message}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] WARNING: {message}"
        self.deployment_log.append(log_entry)
        print(f"⚠️ {message}")
    
    def log_error(self, message: str):
        """Log error message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] ERROR: {message}"
        self.deployment_log.append(log_entry)
        print(f"❌ {message}")

def main():
    """Main deployment execution"""
    print("🚀 Claude Code Hook Deployment System")
    print("=" * 50)
    
    try:
        deployer = HookDeploymentManager()
        report = deployer.deploy_hooks_system()
        
        if report['deployment_summary']['success']:
            print("\n✅ DEPLOYMENT SUCCESSFUL!")
            print("🔄 Please restart Claude Code to activate the hooks system")
            return 0
        else:
            print("\n⚠️ PARTIAL DEPLOYMENT")
            print("🔍 Check the deployment report for details")
            return 1
            
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())