from datetime import datetime,date,timedelta
import time
from openai import OpenAI
import psycopg2
import requests
import pandas as pd

conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='REPLACE_ME',
        host='68.183.13.232',
        port='5432'
    )

client = OpenAI(
    api_key='REPLACE_ME'
)

indicator = 'river'

assistant_id = 'asst_8GQbQr0qL7MigMqIa9Jt1ddV'

current_date = date.today()
previous_week = current_date - timedelta(weeks=1)
week = previous_week.isocalendar()[1]
#week = '4'
year = '2024'


def fetch_data(week,year):
    response = requests.get(f"https://sodma-hasura.sodma.shaqodoonst4d.com/api/rest/river-week-alert/{week}/{year}")
    json_data = response.json()
    df = pd.DataFrame(json_data['station_id_week_full_readings'])
    return df


def insert_data(indicator,report,week,year):
    cur = conn.cursor()

    # Escape quotes in the report string
    sql_query = """
    INSERT INTO ai_report (indicator, report, week, year)
    VALUES (%s, %s, %s, %s)
    """
    sql = cur.mogrify(sql_query, (indicator, report, week, year))
    cur.execute(sql)

    # Commit the transaction
    conn.commit()

    # Close the cursor and the connection
    cur.close()


def generate_report(week,year,file):
  thread = client.beta.threads.create(
      messages=[
          {
              "role": "user", 
            "content": f"Evaluate whether each station is within safe limits, at moderate risk, at high risk, or at full capacity for the week of {week} in the year {year}. Based on your analysis, you will need to draft a report that has the dates of that week as title and highlighting any stations with recent readings that are approaching or exceeding high or full levels, recommending appropriate actions for each.If no recent readings are found for a station include a warning in the report. Remember, timely and accurate reporting is crucial for effective decision-making and ensuring the safety of the communities along these rivers.",
            "attachments": [
                {
                    "file_id": file.id,
                    "tools": [{"type": "code_interpreter"}]
                },
            ]
          }
      ]
  )
  
  run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )
  run_id = run.id
  thread_id = run.thread_id
  
  print(f'Thread created for {week}/{year} successfully with id {thread_id} and run id {run_id}')

  while True:
      run = client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id
      )

      if run.status == 'completed':
          print(f'Run completed for {week}/{year}')
          started_at = datetime.fromtimestamp(run.started_at).strftime('%Y-%m-%d %H:%M:%S')
          completed_at = datetime.fromtimestamp(run.completed_at).strftime('%Y-%m-%d %H:%M:%S')
          print(f'Thread started {started_at} and completed {completed_at}')
          break
      elif run.status == 'failed':
          print(f'Run failed for {week}/{year}')
          break
      else:
          print('Run not completed yet - waiting 30 seconds')
          time.sleep(30)

  thread_messages = client.beta.threads.messages.list(thread_id)
  content = thread_messages.data[0].content[0].text.value
  return content

# for week in range(52,53):
#     df = fetch_data(week,year)
#     df.to_csv('./csv/river-week.csv',index=False)
#     file = client.files.create(file=open('river-week.csv', 'rb'),purpose='assistants')
#     report = generate_report(week,year,file)
#     insert_data(indicator,report,week,year)

df = fetch_data(week,year)
df.to_csv('./csv/river-week.csv',index=False)
river_file = client.files.create(file=open('./csv/river-week.csv', 'rb'),purpose='assistants')
report = generate_report(week,year,river_file)
print(report)
insert_data(indicator,report,week,year)


conn.close()
