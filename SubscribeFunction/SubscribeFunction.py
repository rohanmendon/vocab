import os
import json
import boto3
from datetime import datetime

import sys
sys.path.insert(0, '/opt')

sns_client = boto3.client('sns')
ses_client = boto3.client('ses')
lambda_client = boto3.client('lambda')
dynamo_client = boto3.resource('dynamodb')

# Subscribe a new user, including sending an email confirmation to the user and a notification to the app owner
def lambda_handler(event, context):

    body = json.loads(event["body"])

    # Extract relevant user details
    email_address = body['email']
    list_id = body['list']

    hsk_level = list_id[0]
    char_set = list_id[2:]

    # Write contact to DynamoDB
    try:
        create_contact_dynamo(email_address, list_id, char_set)
        print(f"Success: Contact created in Dynamo - {email_address}, {list_id}.")
    except Exception as e:
        print(f"Error: Failed to create contact in Dynamo - {email_address}, {list_id}.")
        print(e)
        return {
            'statusCode': 502,
            'headers': {
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Origin': '*',
            },
            'body': '{"success" : false}'
        }

    # Send confirmation email from SES
    try:
        send_new_user_confirmation_email_ses(email_address, hsk_level, char_set)
        print(f"Success: Confirmation email sent through SES - {email_address}, {hsk_level}.")
    except Exception as e:
        print(f"Error: Failed to send confirmation email through SES - {email_address}, {hsk_level}.")
        print(e)
        return {
            'statusCode': 502,
            'headers': {
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Origin': '*',
            },
            'body': '{"success" : false}'
        }

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Origin': '*',
        },
        'body': '{"success" : true}'
    }

# Write new contact to Dynamo
def create_contact_dynamo(email_address, list_id, char_set):

    table = dynamo_client.Table(os.environ['TABLE_NAME'])

    date = str(datetime.today().strftime('%Y-%m-%d'))

    sub_status = "subscribed"

    response = table.put_item(
        Item={
                'ListId': list_id,
                'SubscriberEmail' : email_address,
                'DateSubscribed': date,
                'Status': sub_status,
                'CharacterSet' : char_set
            }
        )

    print(f"Contact added to Dynamo - {email_address}, {list_id}.")

def send_new_user_confirmation_email_ses(email_address, hsk_level, char_set):

    # Change subject_line and template to simplified or traditional char version
    if char_set == "simplified":
        subject_line = "Welcome! 欢迎您!"
        email_template = 'confirmation_template_simplified.html'
    else:
        subject_line = "Welcome! 歡迎您!"
        email_template = 'confirmation_template_traditional.html'

    # Open html template file that is packaged with this function's code
    with open(email_template) as fh:
        contents = fh.read()

    email_contents = contents.replace("{level}", hsk_level)

    payload = ses_client.send_email(
        Source = "Haohaotiantian <welcome@haohaotiantian.com>",
        Destination = {
            "ToAddresses" : [
            email_address
            ]
        },
        Message = {
            "Subject": {
                "Charset": "UTF-8",
                "Data": subject_line
                },
            "Body": {
                "Html": {
                    "Charset": "UTF-8",
                    "Data": email_contents
                }
            }
        }
    )