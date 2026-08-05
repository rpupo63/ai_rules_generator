#!/usr/bin/env python3
"""
Setup script for ai-rules-generator
"""

from setuptools import setup
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Package structure - modules are in ai_rules_generator/ directory
# The awesome-cursorrules directory and ai_general_guidelines.md are included as package data
setup(
    name="ai-rules-generator",
    version="1.0.0",
    description="A CLI tool that generates comprehensive AI coding agent rules for Cursor and Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Rules Generator Contributors",
    license="MIT",
    python_requires=">=3.9",
    packages=["ai_rules_generator"],
    package_data={
        "ai_rules_generator": [
            "awesome-cursorrules/**/*",
            "ai_general_guidelines.md",
            "provider_models.json",
        ],
    },
    include_package_data=True,
    install_requires=[
        "ai-model-picker>=0.2.0",
        # Phase 3 - Tree-sitter AST compression
        "tree-sitter>=0.21",
        "tree-sitter-language-pack>=0.2.0",
        # Phase 4 - Graph RAG (PageRank lives in networkx)
        "networkx>=3.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.18.0"],
        "all": [
            "openai>=1.0.0",
            "anthropic>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-rules-generator=ai_rules_generator:main",
            "ai-rules=ai_rules_generator:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Code Generators",
    ],
    keywords=["cursor", "claude", "ai", "rules", "code-generation", "coding-assistant"],
)

