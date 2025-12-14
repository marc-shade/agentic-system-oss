#!/bin/bash
# Kaggle Competition Environment Setup
# Node: macpro51
# Date: 2025-11-24

set -e

echo "🎯 Kaggle Competition Environment Setup"
echo "========================================"
echo ""

# Check if running as user (not root)
if [ "$EUID" -eq 0 ]; then
   echo "❌ Please run as regular user (not sudo)"
   exit 1
fi

echo "📦 Installing Python packages..."
echo ""

# Core ML frameworks
echo "1/5 Installing TensorFlow GPU..."
pip install --user tensorflow[and-cuda] || echo "⚠️  TensorFlow install had warnings (check above)"

echo ""
echo "2/5 Installing Jupyter Lab + extensions..."
pip install --user jupyterlab jupyter ipywidgets notebook jupyterlab-git

echo ""
echo "3/5 Installing visualization libraries..."
pip install --user seaborn plotly kaleido bokeh altair

echo ""
echo "4/5 Installing competition-specific libraries..."
pip install --user \
    albumentations \
    timm \
    transformers \
    datasets \
    optuna \
    wandb \
    mlflow \
    catboost \
    shap \
    eli5

echo ""
echo "5/5 Installing Kaggle utilities..."
pip install --user kaggle-api tqdm joblib

echo ""
echo "✅ Package installation complete!"
echo ""

# Verify installations
echo "🔍 Verifying installations..."
echo ""

python3 -c "
import sys
packages = {
    'TensorFlow': 'tensorflow',
    'Jupyter': 'jupyter',
    'Seaborn': 'seaborn',
    'Plotly': 'plotly',
    'Albumentations': 'albumentations',
    'timm': 'timm',
    'Transformers': 'transformers',
}

print('Package Versions:')
print('-' * 50)
for name, module in packages.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        print(f'✅ {name:20s} {version}')
    except ImportError:
        print(f'❌ {name:20s} NOT INSTALLED')
"

echo ""
echo "🎓 Jupyter Lab setup..."
jupyter labextension list 2>/dev/null || echo "Extensions will be installed on first launch"

echo ""
echo "📁 Competition workspace created at:"
echo "   /mnt/agentic-system/kaggle-competitions/"
ls -d /mnt/agentic-system/kaggle-competitions/*/

echo ""
echo "🚀 To start Jupyter Lab:"
echo "   cd /mnt/agentic-system/kaggle-competitions"
echo "   jupyter lab --no-browser --port=8888"
echo ""

# Check GPU status
echo "🎮 GPU Status Check:"
if nvidia-smi > /dev/null 2>&1; then
    echo "✅ NVIDIA driver working!"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    python3 -c "import tensorflow as tf; print(f'TensorFlow GPUs: {len(tf.config.list_physical_devices(\"GPU\"))}')"
else
    echo "⚠️  NVIDIA driver not working - GPU acceleration disabled"
    echo ""
    echo "To fix GPU:"
    echo "1. Run: sudo bash /mnt/agentic-system/scripts/fix-gpu-driver.sh"
    echo "2. Reboot system"
    echo "3. Run this script again to verify"
fi

echo ""
echo "✅ Setup complete! Ready to compete! 🏆"
echo ""
echo "Next steps:"
echo "1. Fix GPU driver (see above)"
echo "2. Download competition data:"
echo "   kaggle competitions download -c google-tunix-hackathon"
echo "3. Start coding in Jupyter Lab"
