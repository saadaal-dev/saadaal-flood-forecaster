from ..utils.configuration import Config
from ..data_ingestion.load import insert_predicted_river_level_db
from ..data_model.river_level import AlertType, PredictedRiverLevel
from ..data_model.station import get_stations
from mailjet_rest import Client
from datetime import datetime
import pandas as pd
import os

# Load API keys from environment variables
api_key = os.getenv("MAILJET_API_KEY")
api_secret = os.getenv("MAILJET_API_SECRET")


# Ensure credentials are set
if not api_key or not api_secret:
    raise ValueError("MAILJET_API_KEY and MAILJET_API_SECRET must be set as environment variables.")


def get_contact_list_address(list_id):
    """
    Fetch the 'Address' for a given contact list ID using the mailjet_rest library.

    :param list_id: The ID of the contact list.
    :return: The Address of the contact list.
    :raises: Exception if the request fails or the Address is not found.
    """
    # Initialize Mailjet client v3
    mailjet = Client(auth=(api_key, api_secret), version='v3')
    # Get the contact list details
    result = mailjet.contactslist.get(id=list_id)
    
    if result.status_code == 200:
        data = result.json()
        if "Data" in data and len(data["Data"]) > 0:
            return data["Data"][0]["Address"]
        else:
            raise Exception("No data found for the given contact list ID.")
    else:
        print(result)
        raise Exception(f"Failed to fetch contact list details. Status Code: {result.status_code}. Response: {result.text}")


def send_email_to_contact_list(contact_list_address, subject, text_body, html_body):
    """
    Send an email to a Mailjet contact list using its Address field.

    :param contact_list_address: Address of the contact list (e.g., "tsr1234").
    :param subject: Subject of the email.
    :param text_body: Plain text version of the email body.
    :param html_body: HTML version of the email body.
    """
    # Initialize Mailjet Send API v3.1
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    to_email = f'{contact_list_address}@lists.mailjet.com'

    # Prepare the payload
    payload = {
        "SandboxMode": False,
        "Messages": [
            {
                "From": {
                    "Email": "maxime.peter@amadeus.com",
                    "Name": "Saadaal DevOps"
                },
                "To": [
                    {
                        "Email": "florencia.a.etcheverry@gmail.com",
                        "Name": "Subscribers"
                    }
                ],
                "HTMLPart": html_body,
                "Subject": subject,
                "TextPart": text_body
            }
        ]
    }

    result = mailjet.send.create(data=payload)

    if result.status_code == 200:
        print("Email sent successfully!")
    else:
        print(f"Failed to send email. Status Code: {result.status_code}")
        print(f"Response: {result.json()}")


def get_river_station_level_prediction(river_station_id: int, date: datetime) -> float:
    """Get the infered value from the model for a given river station.
    Args:
        river_station_id (int): River station id
        date (datetime): Date to do the inference

    Returns:
        float: Forecasted value for the river level
    """    
    # inference_dataframe = ????
    # Define the dataframe content - to remove - mock
    dataframe_content = {
        'date': ['2024-10-01'],
        'location': ['Bulo Burti'],
        'level_m': [0.0],
        'lag01_level_m': [7.6],
        'y': [-0.25468]
    }

    # Create the DataFrame - to remove
    inference_dataframe = pd.DataFrame(dataframe_content)

    previous_river_level, variation = inference_dataframe.iloc[0].level_m, inference_dataframe.iloc[0].y
    river_level_forecast = previous_river_level + variation
    return river_level_forecast


def run_alerting_module(config: Config, river_station_csv_path: str) -> None:
    
    river_stations = get_stations(river_station_csv_path)

    for river_station in river_stations:

        river_level_forecast = get_river_station_level_prediction(river_station.id, datetime.today())
        forcasted_date= datetime.today() # TODO
        model_name = "TO FILL"  # TODO
        alert_type = AlertType.normal

        print(f"Station {river_station.name} thresholds: {river_station.moderate} (moderate) {river_station.high} (high) {river_station.full} (full)")

        if river_level_forecast < river_station.moderate:
            print(f"Everything fine for river station {river_station.name}. Predicted river level at {river_level_forecast} meters. Moderate threshold at {river_station.moderate}")
        else:
            if river_level_forecast >= river_station.full:
                alert_type = AlertType.full
            elif river_level_forecast >= river_station.high:
                alert_type = AlertType.high
            elif river_level_forecast >= river_station.moderate:
                alert_type = AlertType.moderate
            # send_alert_email(config, river_station, river_level_forecast, alert_type) # TODO

        prediction_row = PredictedRiverLevel(station_number=river_station.id,
                                             location_name=river_station.name,
                                             date=datetime.today(),
                                             forecasted_date=forcasted_date,
                                             level_m=river_level_forecast,
                                             ml_model_name=model_name,
                                             alert_type=alert_type)
        
        insert_predicted_river_level_db(config,prediction_row)

RIVER_STATIONS_CSV_PATH = "/mnt/c/Users/mpeter/git_clones/utg/saadaal-flood-forecaster/static-data/station-data.csv"
run_alerting_module(Config("/mnt/c/Users/mpeter/git_clones/utg/saadaal-flood-forecaster/config/config.ini"), RIVER_STATIONS_CSV_PATH)