from jinja2 import Environment, FileSystemLoader, select_autoescape
import os.path

import google.auth
from google.auth.transport.requests import Request as TransportRequest
from google.oauth2.credentials import Credentials as OauthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.message import EmailMessage
import testing_secrets


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def update_token():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = OauthCredentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(TransportRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("gmail_creds.json", SCOPES)
            # https://developers.google.com/gmail/api/quickstart/python/
            creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token_file:
        token_file.write(creds.to_json())
    return creds


# https://developers.google.com/gmail/api/guides/sending#python
def gmail_send_message(recepient: str, subject: str, body: str):
    creds = update_token()
    #try:
    service = build("gmail", "v1", credentials=creds)
    message = EmailMessage()

    message.add_alternative(body, subtype='html')

    message["To"] = recepient
    message["From"] = testing_secrets.sender_email
    message["Subject"] = subject

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {"raw": encoded_message}
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message Id: {send_message["id"]}')
    #except HttpError as error:
    #    print(f"An error occurred: {error}")
    #    send_message = None


jinja_env = Environment(
    loader=FileSystemLoader('templates/emails'),
    autoescape=select_autoescape(['html', 'xml'])
)


def send_template_email(recepient: str, subject: str, template: str, **kwargs) -> bool:
    #try:
    gmail_send_message(recepient, subject, jinja_env.get_template(template).render(**kwargs))
    #except Exception as e:
    #    print(f"Error sending email: {e}")
    #    return False


if __name__ == '__main__':
    send_template_email(testing_secrets.recepient_email, "henlo wordl", "example.html", message="test123")
