#!/usr/bin/env python3
"""
Setup configuration for Arduino Status Rotation module
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
this_directory = Path(__file__).parent
long_description = (this_directory / "DEPLOYMENT.md").read_text()

setup(
    name="arduino-status-rotation",
    version="1.0.0",
    description="Production status rotation display for agentic system monitoring on Arduino LCD",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="2 Acre Studios",
    author_email="marc@2acrestudios.com",
    url="https://github.com/2acrestudios/arduino-surface",
    packages=find_packages(),
    py_modules=["status_rotation"],
    python_requires=">=3.10",
    install_requires=[
        "pyserial>=3.5",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "pylint>=2.17.0",
        ],
        "security": [
            "bandit>=1.7.5",
            "safety>=2.3.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "arduino-rotation=status_rotation:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="arduino lcd monitoring status rotation agentic-system",
    project_urls={
        "Bug Reports": "https://github.com/2acrestudios/arduino-surface/issues",
        "Source": "https://github.com/2acrestudios/arduino-surface",
        "Documentation": "https://github.com/2acrestudios/arduino-surface/blob/main/DEPLOYMENT.md",
    },
)
