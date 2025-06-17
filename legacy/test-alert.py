import os

import alerting_module

if __name__ == "__main__":
    try:
        # Simulate script logic
        print("Running script...")
        # Raise a sample exception
        raise ValueError("Simulated failure!")
    except Exception as e:
        error_message = f"[An error occurred: {str(e)}"
        print(error_message)

        # Provide the contact list ID
        list_id = os.getenv("CONTACT_LIST_ID")
        # Get contact list address
        contact_list_address = alerting_module.get_contact_list_address(list_id)
        print(f"Contact list address: {contact_list_address}@lists.mailjet.com")
        # Send an email to the contact list
        subject = "Important Notification"
        text_body = "This is a test alert email for the contact list."
        html_body = "<h3>This is a test alert</h3><p>for the contact list.</p>"
        # Send an alert to subscribers
        alerting_module.send_email_to_contact_list(contact_list_address, subject, text_body, html_body)
