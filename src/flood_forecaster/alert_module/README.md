This project automatically sends flood risk alerts via email whenever a high risk level is predicted in the upcoming forecast days. We use [Mailjet](https://www.mailjet.com/) as the email service provider due to its robust API, popularity, and generous free tier.
 
## How It Works
 
- **Trigger:** The alert system checks the predicted river level data. If a high flood risk is detected for any station in the forecast, an email alert is generated and sent.
- **Email Content:** The alert email includes a dynamically generated, styled HTML table summarizing the risk status for each location, along with safety instructions and contact information.
- **Template:** The email uses a customizable HTML template (`alert_template.html`) that is populated with the latest alert data before sending.
 
## Setup Instructions
 
### 1. Create a Mailjet Account
 
- Sign up at [Mailjet](https://www.mailjet.com/).
- We recommend using a Google account for a smoother setup (no manual review required), but any email will work.
- Add and verify your sender email in the Mailjet dashboard.
- Optionally, add your recipients or contact lists directly in Mailjet.
 
### 2. Update the Configuration
 
Edit your `Config.ini` file with the following section:
 
```
[mailjet_config]
sender_email = [your_verified_sender_email]
sender_name = [e.g. "Flood Alert"]
receiver_email = [recipient_email_or_contact_list]
receiver_name = [e.g. "Shaqodoon Team"]
```
 
### 3. Set Environment Variables
 
Export the following variables in your shell or add them to your environment:
 
```sh
export MAILJET_API_KEY="your_mailjet_api_key"
export MAILJET_API_SECRET="your_mailjet_api_secret"
export POSTGRES_PASSWORD="your_postgres_password"
```
 
### 4. Run the Alert Module Manually
 
To test the alert system, run:
 
```sh
python -m src.flood_forecaster.alert_module.main
```
 
---
 
## How the Alert Email Looks
 
- The alert email uses a clean, mobile-friendly HTML template.
- The flood risk table is styled for clarity and readability.
- Safety instructions and contact information are included.
- The template can be customized in `alert_template.html`.
 
---
 
**Note:**  
- Make sure your database is up-to-date with the latest predictions before running the alert.
- You can schedule this script to run automatically (e.g., via a cron job) after new predictions are generated.
 
---
 
**Why Mailjet?**  
Mailjet offers a reliable, developer-friendly API, easy sender/recipient management, and a generous free tier—making it ideal for automated alerting in this project.