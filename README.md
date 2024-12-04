# Repository structure
The repository is structured as follows:
* `src/data-extractor`: Contains the scripts to extract the data for the initial SAADAAL system.
* `src/flood_forecaster/prediction`: Contains ML code for prediction models.
* `src/flood_forecaster/recommendation_algorithm`: Contains code for alert recommendations.
* `src/flood_forecaster/data_ingestion/`: Contains data ingestion modules.
* `src/flood_forecaster/data_ingestion/openmeteo`: Contains the scripts to extract the weather data from the `Open-Meteo API`.
* `src/flood_forecaster/utils`: Contains common helper modules, like `alerting_module` for sending alerts.
* `install`: Contains the scripts to install the required python dependencies on the server.
* `scripts`: Contains the scripts to be scheduled by crontab on the server.
* `static-data`: Contains some data that were captured during the data epxloration phase and that are not yet processed by the scripts.
[//]: # ToDO: *Reorganise* `static-data` *into* `data` *folder and adjust the content to match the models needs.*
* `config`: Contains configuration files for model path, thresholds, ...
* `resource`: Contains serialized models.
* `docs`: Contains documentation on design and architecture details, API, model details and usage, ...


# Linting and secrets detection

* To run the Python linter flake8 on the whole repo, run the command: `tox -e linting`.
* To detect new secrets, compared with the previously created baseline run the command: `tox -e detect-secrets`.
* To run all validations from `tox.ini` just run `tox`

# Server installation
1. Clone the repository at the root path of the server.
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


# Refresh of the server scripts
* To refresh the server scripts, pull the repository and install the required python dependencies.
```bash
cd $BASE_PATH
git pull
bash install/install.sh
```

# Setup of periodic tasks
* Create a cron job to get the weather data every day.
```bash
crontab -e
# Add the last line to the crontab
# m h  dom mon dow   command
0 10 * * * /usr/bin/fetch_river.sh
0 0 * * MON /usr/bin/generate_river.sh
0 0 17 */1 * /usr/bin/fetch_data.sh
0 1 17 */1 * /usr/bin/generate_reports.sh
0 9 * * * WORKDIR=/root/workv2/scripts; ${WORKDIR}/wrapper-script.sh ${WORKDIR}/forecast_weather.sh

# Check the crontab with
crontab -l
```

# Suggested improvements
Those improvements applies to the new scripts (openmeteo) and the existing ones (data-extractor).
* Use alerting_module to capture the script failure/success and send out an email for monitoring/alerting.
* The scripts can be improved by adding error handling and logging.
* The scripts can be improved by adding unit tests.
* The scripts can be improved by adding a CI/CD pipeline.
* The scripts can be improved by adding more documentation.

