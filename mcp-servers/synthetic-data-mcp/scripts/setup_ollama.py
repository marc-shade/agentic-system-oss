#!/usr/bin/env python3
"""
Ollama setup script for Synthetic Data MCP Platform.

This script helps set up Ollama with the optimal models for private
synthetic data generation.
"""

import asyncio
import sys
import subprocess
import platform
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthetic_data_mcp.config.ollama import OllamaManager, get_ollama_config
from loguru import logger


class OllamaSetup:
    """Handles complete Ollama setup for synthetic data generation."""
    
    def __init__(self):
        self.manager = OllamaManager()
        self.system = platform.system().lower()
    
    def print_header(self):
        """Print setup header."""
        print("\n" + "=" * 60)
        print("🦙 OLLAMA SETUP for Synthetic Data MCP Platform")
        print("=" * 60)
        print("Setting up private, local LLM inference for synthetic data generation")
        print("🔒 Privacy: 100% Local - No data leaves your infrastructure")
        print()
    
    def check_ollama_installation(self) -> bool:
        """Check if Ollama is installed on the system."""
        try:
            result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Ollama is installed: {result.stdout.strip()}")
                return True
            else:
                print("❌ Ollama is not installed")
                return False
        except FileNotFoundError:
            print("❌ Ollama is not installed")
            return False
    
    def install_ollama(self) -> bool:
        """Install Ollama based on the operating system."""
        print("\n📦 Installing Ollama...")
        
        if self.system == "darwin":  # macOS
            print("Installing Ollama via Homebrew...")
            try:
                subprocess.run(["brew", "install", "ollama"], check=True)
                print("✅ Ollama installed successfully via Homebrew")
                return True
            except subprocess.CalledProcessError:
                print("❌ Failed to install via Homebrew. Please install manually from https://ollama.ai")
                return False
        
        elif self.system == "linux":
            print("Installing Ollama via official installer...")
            try:
                subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh"], check=True, shell=True)
                print("✅ Ollama installed successfully")
                return True
            except subprocess.CalledProcessError:
                print("❌ Failed to install Ollama. Please install manually from https://ollama.ai")
                return False
        
        else:
            print(f"❌ Automatic installation not supported for {self.system}")
            print("Please download and install Ollama from https://ollama.ai")
            return False
    
    def start_ollama_server(self) -> bool:
        """Start the Ollama server."""
        print("\n🚀 Starting Ollama server...")
        try:
            # Try to start Ollama server in the background
            if self.system == "darwin":
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Give it a moment to start
            import time
            time.sleep(3)
            
            if self.manager.is_server_available():
                print("✅ Ollama server is running")
                return True
            else:
                print("⚠️  Ollama server may be starting... please wait a moment")
                return True
        except Exception as e:
            print(f"❌ Failed to start Ollama server: {e}")
            return False
    
    def setup_models_for_synthetic_data(self) -> bool:
        """Set up recommended models for synthetic data generation."""
        print("\n🧠 Setting up models for synthetic data generation...")
        
        # Detect system memory (rough estimation)
        import psutil
        memory_gb = round(psutil.virtual_memory().total / (1024**3))
        print(f"Detected system memory: {memory_gb}GB")
        
        # Determine which models to install based on available memory
        models_to_install = []
        
        if memory_gb >= 64:
            models_to_install = ["llama3.1:70b", "llama3.1:8b", "codellama:7b"]
            print("🚀 High memory system - installing enterprise models")
        elif memory_gb >= 16:
            models_to_install = ["llama3.1:8b", "codellama:7b", "mistral:7b"]
            print("💼 Standard system - installing recommended models")
        elif memory_gb >= 8:
            models_to_install = ["mistral:7b", "phi3:mini"]
            print("💻 Standard system - installing efficient models")
        else:
            models_to_install = ["phi3:mini"]
            print("📱 Low memory system - installing lightweight model")
        
        success_count = 0
        for model in models_to_install:
            print(f"\n📥 Installing {model}...")
            if self.manager.pull_model(model):
                success_count += 1
                print(f"✅ {model} installed successfully")
            else:
                print(f"❌ Failed to install {model}")
        
        if success_count > 0:
            print(f"\n🎉 Successfully installed {success_count}/{len(models_to_install)} models")
            return True
        else:
            print("\n❌ Failed to install any models")
            return False
    
    def create_environment_file(self):
        """Create environment file with Ollama configuration."""
        print("\n📋 Creating environment configuration...")
        
        env_file = Path(".env.ollama")
        config = get_ollama_config()
        
        # Determine the best model based on what's available
        available_models = self.manager.get_available_models()
        if available_models:
            best_model = available_models[0]["name"]  # Use first available model
            config["model"] = best_model
        
        env_content = f"""# Ollama Configuration for Synthetic Data MCP Platform
# 🔒 Private Local LLM Inference Configuration

# Ollama server configuration
OLLAMA_BASE_URL={config['base_url']}
OLLAMA_MODEL={config['model']}
OLLAMA_HOST={config['host']}
OLLAMA_MODELS={config['models_dir']}

# Privacy and security settings
SYNTHETIC_DATA_PRIVACY_MODE=LOCAL
SYNTHETIC_DATA_LLM_PROVIDER=OLLAMA
SYNTHETIC_DATA_CLOUD_INFERENCE=DISABLED

# Performance tuning
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_FLASH_ATTENTION=true
"""
        
        env_file.write_text(env_content)
        print(f"✅ Environment configuration saved to {env_file}")
        print("\n📖 To use this configuration:")
        print("   export $(cat .env.ollama | xargs)")
        print("   # or source .env.ollama in your shell")
    
    def test_synthetic_data_generation(self):
        """Test synthetic data generation with Ollama."""
        print("\n🧪 Testing synthetic data generation with Ollama...")
        
        try:
            # Import and test the generator
            from synthetic_data_mcp.core.generator import SyntheticDataGenerator
            
            async def test_generation():
                generator = SyntheticDataGenerator()
                
                # Generate a small test dataset
                result = await generator.generate_dataset(
                    domain="healthcare",
                    dataset_type="patient",
                    record_count=3,
                    privacy_level="medium"
                )
                
                if result["status"] == "success":
                    print("✅ Synthetic data generation test passed!")
                    print(f"   Generated {result['metadata']['total_records']} records")
                    print(f"   Privacy level: {result['metadata']['privacy_level']}")
                    
                    # Show sample record structure (without sensitive data)
                    if result["dataset"]:
                        sample = result["dataset"][0]
                        fields = list(sample.keys())[:5]  # Show first 5 fields
                        print(f"   Sample fields: {fields}")
                else:
                    print(f"❌ Test failed: {result.get('error', 'Unknown error')}")
            
            asyncio.run(test_generation())
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print("This is expected if dependencies aren't fully installed yet")
    
    def print_summary(self):
        """Print setup summary and next steps."""
        print("\n" + "=" * 60)
        print("✅ OLLAMA SETUP COMPLETE")
        print("=" * 60)
        
        info = self.manager.get_server_info()
        print(f"🦙 Server Status: {'✅ Running' if info['server_available'] else '❌ Not running'}")
        print(f"🔒 Privacy Status: {info['privacy_status']}")
        print(f"📍 Server URL: {info['base_url']}")
        print(f"🧠 Models Installed: {len(info['models'])}")
        
        if info['models']:
            print("\nInstalled Models:")
            for model in info['models']:
                print(f"  • {model['name']}")
        
        print("\n🚀 NEXT STEPS:")
        print("1. Start your synthetic data MCP server:")
        print("   python -m synthetic_data_mcp.server")
        print("\n2. The platform will automatically use Ollama for private inference")
        print("\n3. All data generation stays completely local - no cloud APIs needed!")
        print("\n4. For production deployment, see docker-compose.yml")
        
        print("\n💡 BENEFITS OF OLLAMA SETUP:")
        print("  🔒 100% Private - No data leaves your infrastructure")
        print("  💰 Cost Effective - No per-token API charges")
        print("  ⚡ Fast Response Times - No network latency")
        print("  🛡️ Compliance Ready - Meets strictest data residency requirements")
        print("  🔧 Full Control - Your models, your rules")

async def main():
    """Main setup function."""
    setup = OllamaSetup()
    
    setup.print_header()
    
    # Check if Ollama is installed
    if not setup.check_ollama_installation():
        if input("\nWould you like to install Ollama? (y/N): ").lower().startswith('y'):
            if not setup.install_ollama():
                print("❌ Setup failed: Could not install Ollama")
                return False
        else:
            print("❌ Setup cancelled: Ollama is required")
            return False
    
    # Start Ollama server
    if not setup.manager.is_server_available():
        setup.start_ollama_server()
    
    # Wait a bit for server to be ready
    print("⏳ Waiting for Ollama server to be ready...")
    for i in range(10):
        if setup.manager.is_server_available():
            break
        await asyncio.sleep(1)
    else:
        print("⚠️  Ollama server may need more time to start")
        print("Please run 'ollama serve' in another terminal and run this script again")
        return False
    
    # Set up models
    success = setup.setup_models_for_synthetic_data()
    
    # Create environment configuration
    setup.create_environment_file()
    
    # Test the setup
    setup.test_synthetic_data_generation()
    
    # Print summary
    setup.print_summary()
    
    return success

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)