"""
Setup
"""
from setuptools import find_packages, setup

# setup(
#     name="flood_forecaster_cli",
#     version="0.1.0",
#     description="A cmdline client for flood_forecaster",
#     classifiers=["Programming Language :: Python :: 3.9"],
#     python_requires=">=3.9, <4",
#     install_requires=["Click", "python-dotenv", "pathlib"],
#     packages=find_packages(),
#     entry_points={
#         "console_scripts": [
#             "flood_forecaster_tool=flood_forecaster_cli.main:cli",
#         ],
#     },
# )


setup(
    name="flood-forecaster-tool",
    version="0.1.1",
    description="A command-line client tool for managing flood_forecaster operations",
    packages=find_packages(where="src"),  # Look for packages under `src/`
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
