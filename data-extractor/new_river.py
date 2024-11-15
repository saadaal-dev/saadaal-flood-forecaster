import requests
from tqdm import tqdm
import pandas as pd
from sqlalchemy import create_engine,text
import os

POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD']

url = 'http://frrims.faoswalim.org/rivers/graph'

def get_data(station_id):
    form_data = {
        "station_id": station_id
    }

    try:
        print(url)
        print(form_data)
        response = requests.post(url, data=form_data, timeout=30)
        print(response)
        response.raise_for_status()  # Raises a HTTPError if the response status code is 4xx or 5xx
        if response.text:  # Check if the response is not empty
            json_response = response.json()
            print(json_response)
            gauge_reading_list = json_response['gaugeReadingList']

            return gauge_reading_list
        else:
            print('Empty response')
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
    except requests.exceptions.RequestException as err:
        print(f'Error occurred: {err}')  # Python 3.6
    except ValueError:
        print('Response is not a valid JSON')
    except requests.exceptions.Timeout:
        print("The request timed out")
        return None

def insert_data(data,station_id):
    df = pd.DataFrame(data)
    df['station_id'] = station_id
    # Convert readingValue to numeric and rename to 'reading'
    df['reading'] = pd.to_numeric(df['readingValue'])

    # Convert dateOfReadingStr to datetime and rename to 'reading_date'
    df['reading_date'] = pd.to_datetime(df['dateOfReadingStr'],format="%d-%m-%Y").dt.date
    # Create a SQLAlchemy engine
    engine = create_engine(f"postgresql://postgres:{POSTGRES_PASSWORD}@68.183.13.232:5432/postgres")

    # Write data to PostgreSQL
    df[['station_id','reading', 'reading_date']].to_sql('temp_table', engine, if_exists='replace', index=False)
    with engine.begin() as connection:
        query = text("""
            INSERT INTO station_river_data (station_id, reading, reading_date)
            SELECT station_id, reading, reading_date
            FROM temp_table
            ON CONFLICT (station_id, reading_date) DO NOTHING
        """)
        connection.execute(query)
stations = [
    {'id': 1, 'name': 'Luuq'},
    {'id': 6, 'name': 'Jowhar'},
    {'id': 2, 'name': 'Dollow'},
    {'id': 5, 'name': 'Bulo Burti'},
    {'id': 3, 'name': 'Bualle'},
    {'id': 4, 'name': 'Belet Weyne'},
    {'id': 17, 'name': 'Bardheere'},
]

for station in tqdm(stations, desc="Processing stations", unit="station"):
    data = get_data(station['id'])
    insert_data(data,station['id'])
