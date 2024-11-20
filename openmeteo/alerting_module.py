from mailjet_rest import Client
import os

# Load API keys from environment variables
api_key = os.getenv("MJ_APIKEY_PUBLIC")
api_secret = os.getenv("MJ_APIKEY_PRIVATE")

# Ensure credentials are set
if not api_key or not api_secret:
    raise ValueError("MJ_APIKEY_PUBLIC and MJ_APIKEY_PRIVATE must be set as environment variables.")


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
                    "Email": "saadaal.dev@gmail.com",
                    "Name": "Saadaal DevOps"
                },
                "To": [
                    {
                        "Email": to_email,
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
