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
4. Get the weather historical data from the Open-Meteo API. It has to be done only one time manually for initialisation
```bash
source $BASE_PATH/data-extractor-venv/bin/activate
cd $BASE_PATH/openmeteo
python3 historical_weather.py
```

