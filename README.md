This repository contains scripts for using the [Open-Meteo](https://open-meteo.com/) Weather API.

# Server installation
1. Clone the repository at the root path of the server.
```bash	
BASE_PATH="/root/workv2"
cd /
git clone https://github.com/saadaal-dev/data-preparation.git $BASE_PATH
```
2. Install the required python dependencies.
```bash
cd $BASE_PATH
bash install/install.sh
```
3. Create a `.env` file in the data-extractor path of the repository and add the following environment variables.
```bash
cd $BASE_PATH/data-extractor
# Edit the file .env and add the following environment variables
OPENAI_API_KEY=
```
4. Get the weather historical data from the Open-Meteo API.
It has to be done only one time manually for initialisation
```bash
source $BASE_PATH/data-extractor-venv/bin/activate
cd $BASE_PATH/openmeteo
python3 historical_weather.py
```
Note that the python installation is done with [virtualenv](https://docs.python.org/3/library/venv.html#creating-virtual-environments), therefore venv has to be activated whenver the python scripts are run.

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
0 9 * * * /root/workv2/scripts/forecast_weather.sh

# Check the crontab with
crontab -l
```

# Suggested improvements
Those improvements applies to the new scripts (openmeteo) and the existing ones (data-extractor).
* Add monitoring and alerting to the scripts in case of failure or data missing.
* The scripts can be improved by adding error handling and logging.
* The scripts can be improved by adding unit tests.
* The scripts can be improved by adding a CI/CD pipeline.
* The scripts can be improved by adding more documentation.

