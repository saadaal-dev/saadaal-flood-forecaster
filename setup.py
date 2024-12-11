"""
Setup
"""
from setuptools import find_packages, setup


# Function to read the requirements.txt file
def read_requirements():
    with open('requirements.txt') as req_file:
        return req_file.read().splitlines()


setup(
    name="flood-forecaster-tool",
    version="0.1.1",
    description="A command-line client tool for managing flood_forecaster operations",
    packages=find_packages(where="src"),  # Look for packages under `src/`
    package_dir={"": "src"},  # Root directory for packages
    entry_points={
        "console_scripts": [
            "flood_forecaster_cli=flood_forecaster_cli.__main__:cli",  # Expose CLI as a console command
        ]
    },
    install_requires=read_requirements(),
    python_requires=">=3.8, <4",
)
