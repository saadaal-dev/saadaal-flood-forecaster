import os
import mailjet_rest
from src.flood_forecaster.data_model.river_level import PredictedRiverLevel
from src.flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.utils.configuration import Config
from sqlalchemy import select
from datetime import datetime, timedelta
import pandas as pd
from src.flood_forecaster.alert_module.flood_status import get_risk_level

def send_alert(mailjet, data):
    # api_key = '99e978fb5666506d248d4609e449382d'
    # api_secret = '8145434250a5e261a31ffeed9cdaaf6d'
    try:
        response = mailjet.send.create(data=data)
        print( response.text)
        if response.status_code != 200:
            raise Exception(f"Mailjet send API returned status code {response}")
           
        return True
    except Exception as e:
        print(f"Mailjet connection failed: {e}")
        return False
           

if __name__ == "__main__":
    """
    This script is part of the flood forecasting and alerting system. It performs the following tasks:
    1. Connects to the database to retrieve predicted river levels and flood risk data.
    2. Analyzes the data to determine flood risk levels for specific dates.
    3. Generates an HTML alert using a predefined template and dynamically inserts flood risk details.
    4. Sends the alert via email using the Mailjet API to notify stakeholders about potential flood risks.
    
    prerequisites:
    - Ensure the following environment variables are set:
        export MAILJET_API_KEY="mailjet_key": The Mailjet API key for sending emails.
        export MAILJET_API_SECRET="mailjet_secret": The Mailjet API secret for authentication.
        export POSTGRES_PASSWORD="db-password": The password for the PostgreSQL database as environment variable.
    """
    # Mailing module
    api_key = os.getenv('MAILJET_API_KEY')
    api_secret = os.getenv('MAILJET_API_SECRET')
    
    if not api_key or not api_secret:
        raise EnvironmentError("MAILJET_API_KEY and MAILJET_API_SECRET must be set as environment variables.")
    mailjet = mailjet_rest.Client(auth=(api_key, api_secret), version='v3.1')
    # mailjet.session.verify = False # Disable SSL verification (insecure)
    
    # Flood analyzing module
    config = Config("config/config.ini")

    target_date = datetime.now() - timedelta(days=13)  # Temporary added timedelta for testing
    print(f"Target date for river_id : {target_date}")
    alert_status_table = get_risk_level(config, date_begin=target_date + timedelta(days=7))
    
    if alert_status_table.empty:
        print("No flood risk observed.")
    else:
        import pandas as pd
        from bs4 import BeautifulSoup

        # Step 1: Your dynamic DataFrame (replace this with your actual script output)
        df = alert_status_table  # This should be the DataFrame you generate dynamically

        # Step 2: Convert DataFrame to HTML table
        table_html = df.to_html(index=False, border=1, classes="alert-table")

        # Step 3: Load the HTML template
        with open("src/flood_forecaster/alert_module/alert_template.html", "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")

        # Step 4: Inject the table into the content section
        table_soup = BeautifulSoup(table_html, "html.parser")
        content_div = soup.find("div", class_="content")
        content_div.append(table_soup)

        # Step 5: Save or send the modified HTML
        final_html = str(soup)
        print(final_html) 
        # # Optional: Save to file
        # with open("alert_with_dynamic_table.html", "w", encoding="utf-8") as file:
        #      file.write(final_html)


        data = {
            'Messages': [
                {
                    'From': {
                        'Email': 'shaqodoon-test@proton.me',
                        'Name': 'Hastati',
                    },
                    'To': [
                        {
                            'Email': 'tm0poa5ar@lists.mailjet.com',
                            'Name': 'Hastati',
                        }
                    ],
                    'Subject': '⚠️ Flood Risk Alert – Please Stay Vigilant',
                    'TextPart': 'This is a test email from Mailjet.',
                    'HTMLPart': final_html
                }
            ]
        }
        if send_alert(mailjet, data):
            print("Alert sent successfully.")















 ######################################
        # print(f"Flood risk observed. Details:\n{alert_status_table}\nSending alert...")
        
        # # Read the HTML template
        # with open("src/flood_forecaster/alert_module/alert_template.html", "r", encoding="utf-8") as f:
        #     html_template = f.read()

        # # Convert alert_status_table to HTML
        # table_html = alert_status_table.to_html(index=False, border=0, classes="alert-table", justify="center")

        # # Insert the table into the template (replace a placeholder or add after a paragraph)
        # final_html = html_template.replace(
        #     '<!-- ALERT_STATUS_TABLE_PLACEHOLDER -->',
        #     f'<h3>Flood Risk Details</h3>{table_html}'
        # )
        # print(final_html)  # Display the final HTML content
        # import pdb; pdb.set_trace()
        # # Use final_html as the HTMLPart of the email
        # data = {
        #     'Messages': [
        #         {
        #             'From': {
        #                 'Email': 'shaqodoon-test@proton.me',
        #                 'Name': 'Hastati',
        #             },
        #             'To': [
        #                 {
        #                     'Email': 'tm0poa5ar@lists.mailjet.com',
        #                     'Name': 'Hastati',
        #                 }
        #             ],
        #             'Subject': '⚠️ Flood Risk Alert – Please Stay Vigilant',
        #             'TextPart': 'This is a test email from Mailjet.',
        #             'HTMLPart': final_html
        #         }
        #     ]
        # }
        # if send_alert(mailjet, data):
        #     print("Alert sent successfully.")
    




    
