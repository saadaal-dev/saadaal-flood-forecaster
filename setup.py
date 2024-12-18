"""
Setup
"""
from setuptools import find_packages, setup

setup(
    name="flood-forecaster-tool",
    version="0.1.1",
    description="A command-line client tool for managing flood_forecaster operations",
    packages=find_packages(where="src"),
    package_dir={"": "src"},  # Root directory for packages
    entry_points={
        "console_scripts": [
            "flood_forecaster_cli=flood_forecaster_cli.main:cli",  # Expose CLI as a console command
        ]
    },
    install_requires=[
        "click>=8.0.0",
        "SQLAlchemy>=2.0.0",
    ],
    python_requires=">=3.9, <4",
)
