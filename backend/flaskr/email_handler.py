from jinja2 import Environment, FileSystemLoader, select_autoescape
import os.path

import google.auth
from google.auth.transport.requests import Request as TransportRequest
from google.oauth2.credentials import Credentials as OauthCredentials
from googleapiclient.discovery import build
import base64
import json
from email.message import EmailMessage
from app import parameters, CarvingOrder


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/spreadsheets"]


def update_token():
    creds = OauthCredentials.from_authorized_user_info(parameters.gmail_token)
    if creds.expired:
        creds.refresh(TransportRequest())
        parameters.gmail_token = json.loads(creds.to_json())
        parameters.upload_changes()
    return creds


# https://developers.google.com/gmail/api/guides/sending#python
def gmail_send_message(recipient: str, subject: str, body: str):
    creds = update_token()
    #try:
    service = build("gmail", "v1", credentials=creds)
    message = EmailMessage()

    message.add_alternative(body, subtype='html')

    message["To"] = recipient
    message["From"] = parameters.sender_email
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


def send_template_email(recipient: str, subject: str, template: str, **kwargs) -> bool:
    try:
        gmail_send_message(recipient, subject, jinja_env.get_template(template).render(**kwargs))
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    return True

def db_to_sheets():
    creds = update_token()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    values = []
    orders = CarvingOrder.query.all()
    for order in orders:
        values.append([order.provided_email, order.carving_text])
    body = {"values": values}
    request = sheet.values().append(spreadsheetId=parameters.carvings_sheet_id, range="A1", valueInputOption="RAW", body=body)
    response = request.execute()
    print(response)
