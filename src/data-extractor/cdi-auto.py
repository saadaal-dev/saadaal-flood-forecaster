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

API_URL = "https://sodma-hasura.sodma.shaqodoonst4d.com/api/rest/all_cdi_alert"

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password=POSTGRES_PASSWORD,
    host="68.183.13.232",
    port="5432",
)

client = OpenAI(api_key=OPENAI_API_KEY)

indicator = "cdi"

assistant_id = "asst_D9qNHGo5PtiYO1iRj4FEVgTi"

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
    df = pd.DataFrame(json_data["all_cdi_alert"])
    return df


def generate_report(report_human_date, file):
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"""
                    Conduct a thorough district-level analysis for the month of {report_human_date}, comparing it to the corresponding months dating back to 2018. The report must be properly formatted markdown with base64 encoded diagrams. Specifically, delve into CDI trends, emphasizing any notable increases or decreases observed over the past three months. Provide a comprehensive report incorporating the following elements:\n\n\t1. District-based analysis for corresponding months.\n\t2. General observations derived from the data.\n\t3. Warnings or areas of concern that merit attention.\n\t4. A conclusive summary encapsulating key findings, supported by exact values.
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
    content = thread_messages.data[0].content[0].text.value
    return content


df = fetch_data()

# convert to csv
df.to_csv("./csv/cdi-data.csv", index=False)

# create file
file = client.files.create(file=open("./csv/cdi-data.csv", "rb"), purpose="assistants")


report_human_date = month["human_format"]
report = generate_report(report_human_date, file)
insert_data(indicator, report, month["month"], month["year"])
print(report)
