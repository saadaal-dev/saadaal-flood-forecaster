import pandas as pd
from bs4 import BeautifulSoup
import os
import mailjet_rest
from src.flood_forecaster.data_model.river_level import PredictedRiverLevel
from src.flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.utils.configuration import Config
from sqlalchemy import select
from datetime import datetime, timedelta
from src.flood_forecaster.alert_module.flood_status import get_latest_date, get_df_by_date
import logging
 
logger = logging.getLogger(__name__)
config = Config("config/config.ini")

 
def deploy_alert(mailjet_client, html_template_path:str, alert_status_table:pd.DataFrame = None):
    """
    Prepares the alert HTML content by injecting the alert status table into the template.
    Args:
        html_template (str): The HTML template as a string.
        alert_status_table (pd.DataFrame): The DataFrame containing flood risk details.
    Returns:
        str: The final HTML content with the alert status table injected.
    """
    # Convert DataFrame to HTML table with custom styling
    table_html = alert_status_table.to_html(
        index=False,
        border=1,
        classes="alert-table",
        escape=False
    )
    # Add custom CSS styling for the table
    custom_style = """
    <style>
    .alert-table {
        border-collapse: collapse;
        width: 100%;
        font-family: Arial, sans-serif;
        margin: 20px 0;
    }
    .alert-table th, .alert-table td {
        border: 1px solid #dddddd;
        text-align: center;
        padding: 8px;
    }
    .alert-table th {
        background-color: #f2a900;
        color: #222;
        font-weight: bold;
    }
    .alert-table tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .alert-table tr:hover {
        background-color: #ffe6b3;
    }
    </style>
    """
    # Load the HTML template
    with open(html_template_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
 
    # Inject the table into the content section
    table_soup = BeautifulSoup(table_html, "html.parser")
    content_div = soup.find("div", class_="content")
    content_div.append(table_soup)
 
    # Inject the custom style into the <head> of the HTML
    if soup.head:
        soup.head.append(BeautifulSoup(custom_style, "html.parser"))
    else:
        soup.insert(0, BeautifulSoup(custom_style, "html.parser"))
 
    # Save or send the modified HTML
    final_html = str(soup)
 
    # # Optional: Save to file
    # with open("alert_with_dynamic_table.html", "w", encoding="utf-8") as file:
    #      file.write(final_html)
 
    data = {
        'Messages': [
            {
                'From': {
                    'Email': f"{config.load_mailjet_config()['sender_email']}",
                    'Name': f"{config.load_mailjet_config()['sender_name']}",
                },
                'To': [
                    {
                        'Email': f"{config.load_mailjet_config()['reciever_email']}",
                        'Name': f"{config.load_mailjet_config()['reciever_name']}",
                    }
                ],
                'Subject': '⚠️ Flood Risk Alert – Please Stay Vigilant',
                'TextPart': 'This is a test email from Mailjet.',
                'HTMLPart': final_html
            }
        ]
    }
    if send_alert(mailjet_client, data):
        print("Alert sent successfully.")
       
def send_alert(mailjet_client, data):
    """
    Sends an alert email using the Mailjet API.
    Args:
        mailjet_client (mailjet_rest.Client): The Mailjet client instance.
        data (dict): The data to be sent in the email, including 'From', 'To', 'Subject', and 'HTMLPart'.
    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    if not mailjet_client:
        logger.error("Mailjet client is not initialized.")
        return False
    try:
        response = mailjet_client.send.create(data=data)
        if response.status_code != 200:
            raise Exception(f"Mailjet send API returned status code {response}")
        logger.info("Mailjet email sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Mailjet connection failed: {e}")
        return False
   
def main():
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
    db_password = os.getenv('POSTGRES_PASSWORD')
   
    if not api_key or not api_secret:
        raise EnvironmentError("MAILJET_API_KEY and MAILJET_API_SECRET must be set as environment variables.")
   
    # Set up clients
    db_client = DatabaseConnection(config, db_password)
    mailjet_client = mailjet_rest.Client(auth=(api_key, api_secret), version='v3.1')
    logger.debug("Postgres and Mailjet client ready")
 
    # Check if the DB was updated within the last 2 days
    today = datetime.now().date()
    today = today.replace(day=10,month=6,year=2025)  # Normalize to midnight
    latest_db_date = get_latest_date(db_client)
    if latest_db_date.date() < today - timedelta(days=2):
        logger.warning("### Exiting process: predicted_river_level has not been updated in the last 2 days")
        exit(1)
   
    # Check if the predicted risk level is full in the forecast day
    flood_status_df = get_df_by_date(db_client, latest_db_date, risk_level='full')
    if flood_status_df.empty:
        logger.info("### Exiting process: No flood risks forecated for the next coming days")
        exit(0)
 
    deploy_alert(mailjet_client,
                 html_template_path="src/flood_forecaster/alert_module/alert_template.html",
                 alert_status_table=flood_status_df)
 
if __name__ == "__main__":
    main()