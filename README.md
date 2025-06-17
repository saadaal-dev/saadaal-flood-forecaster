[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellow.svg)](https://flake8.pycqa.org/)

# 📁 Repository Structure

The project is organized as follows:

| Path | Description |
|------|-------------|
| `src/data-extractor/` |[Obsolete] Scripts to extract raw environmental/hydrological data. |
| `src/flood_forecaster/data_model/` | Utility functions (e.g., alert dispatch, time helpers). |
| `src/flood_forecaster/data_ingestion/` | Ingestion modules for external APIs. |
| `src/flood_forecaster/data_ingestion/openmeteo/` | API integration for weather data from `Open-Meteo`. |
| `src/flood_forecaster/data_ingestion/swalim/` | API integration for weather data from `Open-Meteo`. |
| `src/flood_forecaster/utils/` | Common helper modules (e.g., alert dispatch). |
| `src/flood_forecaster/prediction/` | ML models and training logic for flood prediction. |
| `src/flood_forecaster/recommendation_algorithm/` | Generates actionable alerts based on predictions. |
| `src/flood_forecaster_cli/` | Command-line client for flood_forecaster. |
| `src/tests` | Unit and integration tests.|
| `install/` | Environment setup scripts (Python dependencies). |
| `scripts/` | Cron-scheduled automation jobs for running models. |
| `data/` | Sample environmental data from exploration phase.<br/>*🔧 To be reorganized into `data/` folder.* |
| `config/` | Configuration files: model paths, thresholds, env vars. |
| `resource/` | Serialized trained models and artifacts. |
| `docs/` | Architecture and design details, API docs, data model details and data flows. |

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

## 🔹 Install the CLI

To install the CLI tool, simply run the following command:

```bash
pip install <PATH_TO_CLI_FOLDER>

# or from the repo root path
pip install -e .

```

After installation, you can use the CLI with the `flood_forecaster_cli` command. Example: `flood_forecaster_cli --help`

To uninstall, simply run: `python -m pip uninstall flood_forecaster_cli`

## 🔹 Run the CLI

To run commands with the cli, execute one of the following commands, with appropriate args. 

```bash
flood_forecaster_cli --help
Usage: flood_forecaster_cli [OPTIONS] COMMAND [ARGS]...

  flood_forecaster client tool

Options:
  --help  Show this message and exit.

Commands:
  data-ingestion  Commands for data ingestion
  database-model  Manage Database Schema Operations

flood_forecaster_cli database-model list-db-schemas
Connected to database 'postgres'
Available schemas: ['flood_forecaster', 'hdb_catalog', 'information_schema', 'public']
Schemas in the database:
- flood_forecaster
- hdb_catalog
- information_schema
- public

python -m flood_forecaster_cli.main database-model list-db-schemas
Connected to database 'postgres'
Available schemas: ['flood_forecaster', 'hdb_catalog', 'information_schema', 'public']
Schemas in the database:
- flood_forecaster
- hdb_catalog
- information_schema
- public
```
---

# 🚀 Deployment
## Server installation
### Prerequisites
- Python 3.10.x installed
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
```bash
crontab -e
# Add the last line to the crontab
* 12 * * * <path to the repository>/scripts/bash amadeus_saadaal_flood_forecaster.sh >><path to the repository>/logs/logs_amadeus_saadaal_flood_forecaster.log 2>&1

# Check the crontab with:
crontab -l
```
---

# 🤝 Suggest improvements, contribute

* Report **Issues**: Use the GitHub [issues](https://github.com/saadaal-dev/saadaal-flood-forecaster/issues) tab to report bugs or request features.
* Propose **Enhancements**: To suggest new ideas or improvements please check the [project backlog](https://github.com/orgs/saadaal-dev/projects/1).
* **Contribute**: If you're ready to contribute code, feel free to fork the repo and open a Pull Request against the main branch.
