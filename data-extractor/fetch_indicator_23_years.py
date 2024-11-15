from matplotlib.dates import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine,text
import os

POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD']


def get_last_month():
    last_month = datetime.now() - relativedelta(months=1)
    return last_month.strftime('%b-%Y')


base_date = get_last_month()

print(base_date)
indicators = ['ndvi', 'rainfall', 'cdi']

def month_year_to_first_day(month_year):
    # Mapping of month abbreviations to their numerical values
    months = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
    }
    month, year = month_year.split('-')
    month_number = months[month]
    return f"{year}-{month_number}-01"

# Function to scrape data from the given URL
def scrape_data(indicator,date):
    indicator_url = f"https://dashboard.fsnau.org/climate/{indicator}/{date}"
    response = requests.get(indicator_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('div', class_='indicator-content').find('table')
    df = pd.read_html(str(table))[0]
    if '#' in df.columns:
        df = df.drop('#', axis=1)

    df['region'] = df['Region'].astype(str)
    df['district'] = df['District'].astype(str)
    return df
# Function to calculate the date 6 months prior, in the format "Mon-YYYY"
def calculate_six_months_prior(date):
    current_date = datetime.strptime(date, '%b-%Y')
    six_months_prior = current_date - timedelta(days=182)  
    return six_months_prior.strftime('%b-%Y')

def fetch_data(indicator,start_date,years):
    all_data = None  # Initialize to None
    current_date_str = start_date
    regions_to_include = ["Bakool", "Bay", "Lower Shabelle"]

    for _ in range(2*years):  # 10 periods for 5 years (2 periods per year)
        period_data = scrape_data(indicator,current_date_str)
        # period_data['Period'] = current_date_str  # Add the 'Period' column
        if all_data is None:
            all_data = period_data
        else:
            # Merge data by 'Region' and 'District', adding suffixes to distinguish different periods
            all_data = pd.merge(all_data, period_data, on=['region', 'district'], how='outer', suffixes=('', f'_{current_date_str}'))
        current_date_str = calculate_six_months_prior(current_date_str)
    all_data = all_data[all_data['region'].isin(regions_to_include)]
    columns_with_underscore = [col for col in all_data.columns if '_' in col]
    all_data.drop(columns=columns_with_underscore, inplace=True)
    month_columns = [col for col in all_data.columns if '-' in col]
    month_columns.sort(key=lambda date: datetime.strptime(date, '%b-%Y'))
    new_column_order = ['region', 'district'] + month_columns
    all_data = all_data.reindex(columns=new_column_order)
    return all_data

def transform_data(data,base_date):
    df = pd.DataFrame(data)
    melted_df = df.melt(id_vars=["region", "district"], var_name="Month_Year", value_name="value")

    # Transform Month_Year to YYYY-MM-01 format
    melted_df['month'] = pd.to_datetime(melted_df['Month_Year'].apply(month_year_to_first_day))
    melted_df.drop('Month_Year', axis=1, inplace=True)
    melted_df['indicator'] = indicator
    base_date_format = month_year_to_first_day(base_date)
    melted_df = melted_df[melted_df['value'].notnull()]
    #melted_df = melted_df[melted_df['month'] == base_date_format]
    
    return melted_df

def insert_data(transformed_data):
    engine = create_engine(f"postgresql://postgres:{POSTGRES_PASSWORD}@68.183.13.232:5432/postgres)
    transformed_data.to_sql('temp_indicator_table', engine, if_exists='replace', index=False)
    with engine.begin() as connection:
        query = text("""
            INSERT INTO indicator_data (region, district, value, month, indicator)
            SELECT region, district, value, month, indicator
            FROM temp_indicator_table
            ON CONFLICT (region, district, value, month, indicator) DO NOTHING
        """)
        connection.execute(query)
# Fetch the data
for indicator in indicators:
    data = fetch_data(indicator,base_date,23)
    transformed_data = transform_data(data,base_date)
    if transformed_data.empty:
        continue
    #insert_data(transformed_data)
    transformed_data.to_csv(f'{indicator}_data_sws.csv',index=False)
    
