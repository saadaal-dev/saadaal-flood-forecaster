[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellow.svg)](https://flake8.pycqa.org/)

# 📁 Repository Structure

The project is organized as follows:

| Path                                             | Description                                                                                                        |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `src/flood_forecaster/data_model/`               | Utility functions (e.g., alert dispatch, time helpers).                                                            |
| `src/flood_forecaster/data_ingestion/`           | Ingestion modules for external APIs.                                                                               |
| `src/flood_forecaster/data_ingestion/openmeteo/` | API integration for weather data from `Open-Meteo`.                                                                |
| `src/flood_forecaster/data_ingestion/swalim/`    | API integration for weather data from `Open-Meteo`.                                                                |
| `src/flood_forecaster/utils/`                    | Common helper modules (e.g., alert dispatch).                                                                      |
| `src/flood_forecaster/prediction/`               | ML models and training logic for flood prediction.                                                                 |
| `src/flood_forecaster/recommendation_algorithm/` | Generates actionable alerts based on predictions.                                                                  |
| `src/flood_forecaster_cli/`                      | Command-line client for flood_forecaster.                                                                          |
| `src/tests`                                      | Unit and integration tests.                                                                                        |
| `install/`                                       | Environment setup scripts (Python dependencies).                                                                   |
| `scripts/`                                       | Cron-scheduled automation jobs for running models. See [Scripts Reference](docs/SCRIPTS_REFERENCE.md) for details. |
| `sql/`                                           | Database schema and setup scripts for PostgreSQL.                                                                  |
| `data/interim`                                   | Data used for ML model training and validation.                                                                    |
| `data/raw`                                       | Sample environmental data from exploration phase.                                                                  |
| `data/static`                                    | Static metadata of stations and locations for weather and river data.                                              |
| `config/`                                        | Configuration files: model paths, thresholds, env vars.                                                            |
| `models/`                                        | Serialized trained models and artifacts.                                                                           |
| `docs/`                                          | Architecture and design details, API docs, data model details and data flows.                                      |
| `legacy/data-extractor/`                         | [Obsolete] Scripts to extract raw environmental/hydrological data.                                                 |
| `pyproject.toml`                                 | Root project configuration defining a workspace                                                                    |

---

# 🧪 Code Guidelines & Validation

- Follow [PEP8](https://peps.python.org/pep-0008/) for Python code.
- Write clean, readable code and comment where appropriate.
- Use descriptive commit messages.
- Ensure that your code passes all linting and unit tests before submitting.

## ✅ Pull Request Checklist

Before submitting a PR, please ensure:

- [ ] The code runs correctly locally.
- [ ] All tests pass and the code is linted.
- [ ] Documentation is updated if needed.
- [ ] You’ve added meaningful comments where applicable.

## 🔹 Linting and secrets detection

* To run the Python linter flake8 on the whole repo, run the command: `tox -e linting`.
* To detect new secrets, compared with the previously created baseline run the command: `tox -e detect-secrets`.
* To run all validations from `tox.ini` just run `tox`

---

## 📦 Install the CLI

> [!NOTE]
> TODO: Simplify install.sh by making use of pyproject.toml and uv packager

### Recommended Installation (using install.sh)

The recommended way to install the flood forecaster CLI is using the provided installation script:

```bash
# Clone the repository
git clone https://github.com/saadaal-dev/saadaal-flood-forecaster.git
cd saadaal-flood-forecaster

# Run the installation script
bash install.sh
```

The `install.sh` script will:

- Create a virtual environment in `.venv/`
- Install all required dependencies from `pyproject.toml`
- Install the CLI package in editable mode
- Set up the necessary permissions for scripts

Create a file `.env` at the root of the project to set the passwords (such file will stay local as part of .gitignore):

- POSTGRES_PASSWORD is required to connect to the Shaqodoon database.

```txt
POSTGRES_PASSWORD="XXX"
```

### Manual Installation

Alternatively, you can install manually:

```bash
# Create and activate virtual environment
curl -LsSf https://astral.sh/uv/install.sh | sh
# Choose the appropriate Python version
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies and CLI package from pyproject.toml
# if needed generate requirements.txt from same pyproject
uv pip install -e .[dev]
uv pip install -e .
uv pip compile pyproject.toml -o requirements.txt
```

### Using the CLI

After installation, activate the virtual environment and use the CLI:

```bash
# Use CLI via script exec
flood-cli --help

# Use CLI with direct module call
python -m flood_forecaster_cli.main ml list-models

```

The CLI is configured in `setup.py` as a console script entry point, making the `flood_forecaster_cli` command available
system-wide when the virtual environment is active.

To uninstall, simply run: `python -m pip uninstall flood-forecaster-tool`

### Configuration Notes

The CLI configuration is managed through `pyproject.toml`.

Advanced users can manually adjust the `PATH` or create custom shell aliases for convenience.
For example, to create a shell alias, you can add the following line to your `.bashrc` or `.zshrc`:

```bash
alias my_flood_cli='source /full/path/to/saadaal-flood-forecaster/.venv/bin/activate && flood-cli'
```

---

# 🚀 Deployment
## Server installation
### Prerequisites
- Python 3.12.x installed
- PostgreSQL installed and running
- Database configured (if not, see [Database Setup](#-database-setup))
- CRON daemon running:

To check:
```bash
sudo service cron status
```
To start:
```bash
sudo service cron start
```
### Step by step guide
1. Clone the repository at the root path of the target server.

```bash
BASE_PATH="/root/Amadeus"
cd $BASE_PATH
git clone https://github.com/saadaal-dev/saadaal-flood-forecaster.git
```
2. Create a `.env` file repository root level and add the following environment variables.
```bash
cd saadaal-flood-forecaster/
touch .env
```
```bash
export POSTGRES_PASSWORD=<database-password>
```
3. Install the application and the required python dependencies.
```bash
bash install.sh
```

## Alert setup
Checkout the alert README.md here: `src/flood_forecaster/alert_module/README.md`.

## Setup of periodic tasks
The script to be set up in the CRON is the following: [amadeus_saadaal_flood_forecaster.sh](scripts/amadeus_saadaal_flood_forecaster.sh).
The goal of this file is to run sequentially all the modules from data ingestion to alert sending.
The logs of the CRON app will be stored in this folder: `logs/`. The creation of this folder is managed by the [install.sh](install.sh) script.

📖 **For detailed information about all available scripts, see the [Scripts Reference Guide](docs/SCRIPTS_REFERENCE.md)
**.
```bash
crontab -e
# Add the last line to the crontab
* 12 * * * <path to the repository>/scripts/bash amadeus_saadaal_flood_forecaster.sh >><path to the repository>/logs/logs_amadeus_saadaal_flood_forecaster.log 2>&1

# Check the crontab with:
crontab -l
```
---

## 🗄️ Database Setup

The flood forecaster uses PostgreSQL to store historical data, predictions, and metadata. Follow these steps to set up
the database:

### Prerequisites

- PostgreSQL 15+ installed and running
- Database user with CREATE privileges

### Quick Setup

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15

   # Ubuntu/Debian
   sudo apt-get install postgresql-15
   sudo systemctl start postgresql
   ```

2. **Create the database schema**:
   ```bash
   # From the project root directory
   psql -U postgres -d postgres -f sql/database_bootstrap.sql
   ```

3. **Add performance indexes** (optional but recommended):
   ```bash
   psql -U postgres -d postgres -f sql/database_indexes.sql
   ```

### Database Files

| File                         | Description                                                      |
|------------------------------|------------------------------------------------------------------|
| `sql/database_bootstrap.sql` | Creates the `flood_forecaster` schema with all 5 required tables |
| `sql/database_indexes.sql`   | Adds performance indexes for optimized queries                   |
| `sql/database_views.sql`     | Defines commonly used database views for easier querying         |

### Database Schema Overview

The database includes the following tables:

- **`historical_river_level`** - Historical river level measurements
- **`predicted_river_level`** - ML model predictions for future river levels
- **`historical_weather`** - Historical weather data for model training
- **`forecast_weather`** - Weather forecast data for predictions
- **`river_station_metadata`** - Metadata about river monitoring stations

For a detailed visual representation of the database schema and table relationships, see
the [database model diagram](docs/flood_forecaster_datamodel.md).

---

# 🤝 Suggest improvements, contribute

* Report **Issues**: Use the GitHub [issues](https://github.com/saadaal-dev/saadaal-flood-forecaster/issues) tab to report bugs or request features.
* Propose **Enhancements**: To suggest new ideas or improvements please check the [project backlog](https://github.com/orgs/saadaal-dev/projects/1).
* **Contribute**: If you're ready to contribute code, feel free to fork the repo and open a Pull Request against the main branch.
