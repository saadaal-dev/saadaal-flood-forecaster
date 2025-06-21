# fetch data from api
import calendar
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import psycopg2
import requests
from openai import OpenAI

POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

API_URL = "https://sodma-hasura.sodma.shaqodoonst4d.com/api/rest/all_rainfall_alert"

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password=POSTGRES_PASSWORD,
    host="68.183.13.232",
    port="5432",
)

client = OpenAI(api_key=OPENAI_API_KEY)

indicator = "rainfall"

assistant_id = "asst_BpPgQIOF7cv59rU6w2UgmCQ3"

now = datetime.now()
last_month = now - timedelta(days=30)
last_month_number = last_month.month
year = last_month.year
month_name = calendar.month_name[last_month_number]
month = {
    "month": str(last_month_number),
    "year": str(year),
    "human_format": f"{month_name} {year}",
}

# for month in range(1,11):
#     month_name = calendar.month_name[month]
#     month_year = {
#         'month': str(month),
#         'year': '2023',
#         'human_format': f'{month_name} 2023'
#     }
#     months.append(month_year)


def insert_data(indicator, report, month, year):
    cur = conn.cursor()

    # Escape quotes in the report string
    sql_query = """
    INSERT INTO ai_report (indicator, report, month, year)
    VALUES (%s, %s, %s, %s)
    """
    # mogrified_query = cur.mogrify(sql_query, (indicator, report, month, year))
    sql = cur.mogrify(sql_query, (indicator, report, month, year))
    cur.execute(sql)

    # Commit the transaction
    conn.commit()

    # Close the cursor and the connection
    cur.close()


def fetch_data():
    response = requests.get(API_URL)
    json_data = response.json()
    df = pd.DataFrame(json_data["all_rainfall_alert"])
    return df


def generate_report(report_human_date, file):
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"""
                    Using the rainfall data and considering the Somali weather seasons. Create a comprehensive properly formatte markdown district-based rainfall analysis report with base64 encoded diagrams for  {report_human_date}. Include prediction for the following month rainfall based on the historical data, Somali weather seasons and noting that 1991-2, 1994-5, 1997-8, 2002-3, 2006-7, 2009-10, 2006 and October to December 2023 these districts were affected by El Niño in which more rainfall than usual was reported causing floods. Ensure the report covers the essential elements outlined in the instructions and presents the findings in an informative and actionable manner.
                """,
                "attachments": [
                    {"file_id": file.id, "tools": [{"type": "code_interpreter"}]},
                ],
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )
    print(
        f"Thread created for {report_human_date} successfully with id {thread.id} and run id {run.id}"
    )

    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            print(f"Run completed for {report_human_date}")
            started_at = datetime.fromtimestamp(run.started_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            completed_at = datetime.fromtimestamp(run.completed_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            print(f"Thread started {started_at} and completed {completed_at}")
            break
        elif run.status == "failed":
            print(f"Run failed for {report_human_date}")
            break
        else:
            print("Run not completed yet - waiting 30 seconds")
            time.sleep(30)

    thread_messages = client.beta.threads.messages.list(thread.id)
    print(thread_messages.data[0])
    content = thread_messages.data[0].content[0].text.value
    return content


df = fetch_data()

# convert to csv
df.to_csv("./csv/long-rainfall-data.csv", index=False)

# create file
file = client.files.create(
    file=open("csv/long-rainfall-data.csv", "rb"), purpose="assistants"
)


report_human_date = month["human_format"]
report = generate_report(report_human_date, file)
insert_data(indicator, report, month["month"], month["year"])
print(report)
