from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
import requests
import os

POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD']

conn_string = f"postgresql://postgres:{POSTGRES_PASSWORD}@68.183.13.232:5432/postgres"

conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

def fetch_station_id(station_name):
    cursor.execute(f"SELECT id FROM station WHERE name = '{station_name}'")
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    else:
        return None

def insert_data(df):
    for index, row in df.iterrows():
        station = row['station']
        reading = row['reading']
        reading_date = row['reading_date']

        station_id = fetch_station_id(station)
        if station_id is None:
            print(f"No station found with name {station}")
            continue
        sql_query = """
        INSERT INTO station_river_data (station_id, reading, reading_date)
        VALUES (%s, %s, %s)
        ON CONFLICT (station_id,reading_date) DO NOTHING
        """
        sql = cursor.mogrify(sql_query, (station_id, reading, reading_date))
        cursor.execute(sql)
    conn.commit()


def scrape_data():
    url = 'https://frrims.faoswalim.org/rivers/levels'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', id='maps-data-grid')
    df = pd.read_html(str(table))[0]
    df = df.head(7)
    new_df = pd.DataFrame()
    new_df['station'] = df['Station'].astype(str)
    new_df['reading'] = pd.to_numeric(df['Observed River Level (m)'], errors='coerce')
    new_df['reading_date'] = pd.to_datetime(df['Date'],format="%d-%m-%Y").dt.date

    return new_df    
    return df


data = scrape_data()
print(data)
insert_data(data)

