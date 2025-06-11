[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellow.svg)](https://flake8.pycqa.org/)

## 📁 Repository Structure

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

## 🧪 Code Guidelines & Validation

- Follow [PEP8](https://peps.python.org/pep-0008/) for Python code.
- Write clean, readable code and comment where appropriate.
- Use descriptive commit messages.
- Ensure that your code passes all linting and unit tests before submitting.

### ✅ Pull Request Checklist

Before submitting a PR, please ensure:
- [ ] The code runs correctly locally.
- [ ] All tests pass and the code is linted.
- [ ] Documentation is updated if needed.
- [ ] You’ve added meaningful comments where applicable.

### 🔹 Linting and secrets detection

* To run the Python linter flake8 on the whole repo, run the command: `tox -e linting`.
* To detect new secrets, compared with the previously created baseline run the command: `tox -e detect-secrets`.
* To run all validations from `tox.ini` just run `tox`

### 🔹 Install the CLI

To install the CLI tool, simply run the following command:

```bash
pip install <PATH_TO_CLI_FOLDER>

# or from the repo root path
pip install -e .

```

After installation, you can use the CLI with the `flood_forecaster_cli` command. Example: `flood_forecaster_cli --help`

To uninstall, simply run: `python -m pip uninstall flood_forecaster_cli`

### 🔹 Run the CLI

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

## 🚀 Deployment [🔧 to be reviewed]
### Server installation
1. Clone the repository at the root path of the target server.
```bash	
BASE_PATH="/root/flood-forecaster"
cd /
git clone https://github.com/saadaal-dev/saadaal-flood-forecaster.git $BASE_PATH
```
2. Install the required python dependencies.
```bash
cd $BASE_PATH
bash install/install.sh
```
3. Create a `.env` file in the `data-extractor` path of the repository and add the following environment variables.
```bash
cd $BASE_PATH/src/data-extractor
# Edit the file .env and add the following environment variables
OPENAI_API_KEY=  # TODO remove
POSTGRES_PASSWORD=
```
4. Get the weather historical data from the Open-Meteo API.
It has to be done only one time manually for initialisation
```bash
source $BASE_PATH/src/data-extractor-venv/bin/activate
OPENMETEO_PATH="${BASE_PATH}/src/flood_forecaster/data_ingestion/openmeteo"
cd ${OPENMETEO_PATH}
python3 historical_weather.py
```
Note that the python installation is done with [virtualenv](https://docs.python.org/3/library/venv.html#creating-virtual-environments), therefore venv has to be activated whenver the python scripts are run.

5. Configure email alert to a contact list with Mailjet API
* Create a .env_mailjet file in the `utils` folder including the Mailjet API credentials for your account, and the contact list_ID
```bash
UTILS_PATH="${BASE_PATH}/src/flood_forecaster/utils"
cd ${UTILS_PATH}
# Edit the file .env_apicreds and add the following environment variables
MAILJET_API_KEY=
MAILJET_API_SECRET=
CONTACT_LIST_ID=
```
* `from utils import alerting_module` to your python script and call `alerting_module.send_email_to_contact_list()` to send an alert in case of failure, or when specific alerting criteria are being reached


### Refresh of the server scripts
* To refresh the server scripts, pull the repository and install the required python dependencies.
```bash
cd $BASE_PATH
git pull
pip install -e .
```

### Setup of periodic tasks
* Create a cron job to get the weather data every day.
```bash
crontab -e
# Add the last line to the crontab
# m h  dom mon dow   command
#TODO: Schedule flood_forecaster jobs

# Check the crontab with
crontab -l
```
---

## 🤝 Suggest improvements, contribute

* Report **Issues**: Use the GitHub [issues](https://github.com/saadaal-dev/saadaal-flood-forecaster/issues) tab to report bugs or request features.
* Propose **Enhancements**: To suggest new ideas or improvements please check the [project backlog](https://github.com/orgs/saadaal-dev/projects/1).
* **Contribute**: If you're ready to contribute code, feel free to fork the repo and open a Pull Request against the main branch.
