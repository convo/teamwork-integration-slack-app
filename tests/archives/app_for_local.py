import os
import logging
import json
import re
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

from slack_sdk import WebClient
from slack_sdk.web import SlackResponse
from slack_bolt.authorization import AuthorizeResult

from slack_bolt import App, Ack, Respond
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from teamwork_integration_slack_app.teamwork_api.tw_auth import TW_Connector, Employee_Leave_Request

load_dotenv()

#logging.basicConfig(level=logging.DEBUG)
date_format = "%Y-%m-%dT%H:%M:%S%z"

# Initializes app with bot token and signing secret
def authorize(client: WebClient):
    
    token = os.environ["SLACK_BOT_TOKEN"]
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    
    return AuthorizeResult.from_auth_test_response(
        auth_test_response=client.auth_test(token=token),
        bot_token=token,
    )

app = App(
    authorize=authorize,
    process_before_response=True
    )

@app.action({"type": "workflow_step_edit", "callback_id": "leave_request"})
def edit(body: dict, ack: Ack, client: WebClient):
    
    ack()
    configuration_view = client.views_open(
        trigger_id = body["trigger_id"],
        view = {
            "type": "workflow_step",
            "callback_id": "vto_workflow_view",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "VTO Request Trigger Setting"
                    },
                },
                {
                    "type": "input",
                    "block_id": "vto_form_receipient_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "vto_form_receipient"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Place the person who reacted with email address in here please."
                    }
                },
                {
                    "type": "input",
                    "block_id": "vto_channel_id_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "vto_channel_id"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Place the channel variable where the react was used in please."
                    }
                },
                {
                    "type": "input",
                    "block_id": "vto_message_link_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "vto_message_link"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Place \"Link to message reacted on\" variable in here please."
                    }
                }
            ]
        }
    )

@app.view("vto_workflow_view")
def save(ack: Ack, client: WebClient, body: dict):
    ack()
    state_values = body["view"]["state"]["values"]
    
    response = client.api_call(
        api_method = "workflows.updateStep",
        json = {
            "workflow_step_edit_id": body["workflow_step"]["workflow_step_edit_id"],
            
            "inputs": {
                "vtoFormReceipient": {
                        "value": state_values["vto_form_receipient_input"]["vto_form_receipient"]["value"],
                    },
                "vtoChannelSource": {
                        "value": state_values["vto_channel_id_input"]["vto_channel_id"]["value"],
                    },
                "vtoMessageLink": {
                        "value": state_values["vto_message_link_input"]["vto_message_link"]["value"],
                    },
                },
            "outputs": [
                {
                    "name": "vtoFormReceipient",
                    "type": "text",
                    "label": "VTO Form Receipient",
                },
                {
                    "name": "vtoChannelSource",
                    "type": "text",
                    "label": "Channel Source",
                },
                {
                    "name": "vtoMessageLink",
                    "type": "text",
                    "label": "Message Link",
                },
            ],
        },
    )

@app.action("open-leave-request-form")
def button_click(ack: Ack, body: dict, respond: Respond, client: WebClient):
    print('--------------- open-leave-request-form ---------------')
    ack()
    logging.info(body)
    
    message_mention = re.search(r"<@(.*?)>",body["message"]["blocks"][0]["text"]["text"]).group(1)
    
    res = client.views_open(
        trigger_id = body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "leave-request-submission",
            "title": {
                "type": "plain_text",
                "text": "VTO Request Form",
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit",
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel",
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "vto_start_time_input",
                    "element": {
                        "type": "datetimepicker",
                        "action_id": "vto_start_time",
                        "initial_date_time": int(datetime.today().replace(microsecond=0, second=0, minute=0).timestamp())
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "VTO Start Time",
                    }
                },
                {
                    "type": "input",
                    "block_id": "vto_end_time_input",
                    "element": {
                        "type": "datetimepicker",
                        "action_id": "vto_end_time",
                        "initial_date_time": int((datetime.today().replace(microsecond=0, second=0, minute=0) + timedelta(hours=1)).timestamp())
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "VTO End Time",
                    }
                }
            ],
            "private_metadata": f'{{\
                "thread_ts": "{body["container"]["thread_ts"]}",\
                "message_ts": "{body["container"]["message_ts"]}",\
                "response_url": "{body["response_url"]}",\
                "message_mention": "{message_mention}",\
                "channel_id": "{body["container"]["channel_id"]}"\
                }}'
        }
    )

@app.view("leave-request-submission")
def handle_submission(ack: Ack, body: dict, client: WebClient):
    print('--------------- leave-request-submission ---------------')
    ack()
    
    private_metadata = json.loads(body["view"]["private_metadata"])
    response_url = private_metadata["response_url"]
    message_ts = private_metadata["message_ts"]
    message_mention = private_metadata["message_mention"]
    thread_ts = private_metadata["thread_ts"]
    channel_id = private_metadata["channel_id"]
    vto_start_time = body["view"]["state"]["values"]["vto_start_time_input"]["vto_start_time"]["selected_date_time"]
    vto_end_time = body["view"]["state"]["values"]["vto_end_time_input"]["vto_end_time"]["selected_date_time"]
    
    # Validate inputs
    if vto_start_time >= vto_end_time or vto_end_time <= vto_start_time:
        ack({
            "response_action": "errors",
            "errors": {
                "vto_start_time_input": "This cannot be more than or equal to the VTO End Time.",
                "vto_end_time_input": "This cannot be less than or equal to the VTO Start Time."
            }
        })
        return
    
    logging.info(body)
    
    user = client.users_info(user=body["user"]["id"])
    user_id = user["user"]["id"]
    user_email = user["user"]["profile"]["email"]
    user_tz_offset = user["user"]["tz_offset"]

    print(f'{vto_start_time}\n{vto_end_time}')
    print(f'{os.environ.get("TEAMWORK_URL")}\n')
    
    tw_connector = TW_Connector(base_url = os.environ.get("TEAMWORK_URL"),
                                portal = os.environ.get("TEAMWORK_PORTAL"),
                                code = os.environ.get("TEAMWORK_CODE"),
                                username = os.environ.get("TEAMWORK_USERNAME"),
                                password = os.environ.get("TEAMWORK_PASSWORD"))
    tw_connector._authenicate_tw()
    
    # Find the employee information by email
    response = tw_connector.get_employee_by_email(user_email)
    if response.json()['Total'] == 0:
        
        # Call the chat_postMessage or chat_postEphemeral or chat_update
        ack({"response_action": "clear"})
        
        if (user_id == message_mention):
            response = client.chat_delete(channel=channel_id,ts=message_ts)
        
        response = client.chat_postMessage(
            #user=user_id,
            username="Error",
            blocks=[{"type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Sorry, <@{user_id}>, you cannot request VTO because you are not a registered employee in the Teamwork system. Please contact the admin for help."
                }
            }],
            icon_url="https://convorelay.com/wp-content/uploads/2023/01/convo_bot_error_512.png",
            thread_ts=f"{thread_ts}",
            channel=f"{channel_id}",
            text=f"Sorry, <@{user_id}>, you cannot take VTO request because you are not registered employee in Teamwork system. Please contact admin for help."
            #text=f"Good news! <@{user_id}|{user_name}> has submitted successfully!\nVTO Start Time: {formatted_vto_start_time}\nVTO End Time: {formatted_vto_end_time}\nVTO Timezone: {vto_timezone_label}"
        )
        return
    else:
        
        tw_employee = response.json()['Data']

        # Get the active location of an employee's
        my_tw_location = []
        response = tw_connector.request(request_method="GET",
                                        endpoint=f"/api/employees/{tw_employee[0]['Id']}/locations",
                                        payload="")
        tw_locations = response.json()
        
        if not len(tw_locations) == 0:
            for loc in tw_locations:
                if loc['IsDefault']:
                    response = tw_connector.get(f"/api/locations/{loc['BusinessId']}").json()
                    response = json.dumps(response)
                    loc['TimeZone'] = json.loads(response)['TimeZone']
                    my_tw_location = loc
                    
        print(my_tw_location)
        
        # Create a timedelta object represents Slack's timezone offset
        vto_start_time_timestamp = datetime.fromtimestamp(vto_start_time)
        vto_end_time_timestamp = datetime.fromtimestamp(vto_end_time)
        
        # Create a timedelta object represents Slack's timezone offset
        my_slack_offset_tz = timezone(timedelta(seconds=user_tz_offset))

        vto_start_time_dt = vto_start_time_timestamp.replace(tzinfo=my_slack_offset_tz)
        vto_end_time_dt = vto_end_time_timestamp.replace(tzinfo=my_slack_offset_tz)
        
        # Parse the location's timezone offset
        my_tw_loc_offset = my_tw_location['TimeZone'][1:-1].split(") ")[0]
        my_tw_loc_offset_timetz = datetime.strptime(my_tw_loc_offset, "UTC%z").timetz()
        
        # Create a timedelta object representing the time zone offset
        my_tw_loc_offset_timedelta = timedelta(hours=my_tw_loc_offset_timetz.hour,
                                               minutes=my_tw_loc_offset_timetz.minute)
        
        # Create a time zone object for the new time zone
        my_tw_loc_tz_dt = timezone(my_tw_loc_offset_timedelta)
        
        # Convert the datetime object to the new time zone
        converted_vto_start_time = vto_start_time_dt.astimezone(my_tw_loc_tz_dt)
        converted_vto_end_time = vto_end_time_dt.astimezone(my_tw_loc_tz_dt)
        
        # Get the list of leave types
        response = tw_connector.get('/api/leave/leavetypes')
        tw_leave_types = response.json()
        #print(f'--- List of Teamwork\'s Leave Types ---\n{tw_leave_types}\n---')
        
        # Get a VTO Slack leave type
        if not len(tw_leave_types) == 0:
            for i in tw_leave_types:
                if i["Title"] == "VTO: Slack" or i["Code"] == "VTOSLACK":
                    selected_leave_type = i

        # Initialize a leave request
        tw_leave_request = Employee_Leave_Request(EmpId = tw_employee[0]["Id"],
                                                  EmpName = tw_employee[0]["FullName"],
                                                  Employees = [{"Id": tw_employee[0]["Id"],
                                                                "Title": tw_employee[0]["FullName"]}],
                                                  Start = converted_vto_start_time.date().strftime(date_format),
                                                  End = converted_vto_end_time.date().strftime(date_format),
                                                  StartTime = converted_vto_start_time.strftime(date_format),
                                                  EndTime = converted_vto_end_time.strftime(date_format),
                                                  TypeId=selected_leave_type['Id'],
                                                  LeaveTypes = [selected_leave_type],
                                                  MinDate = datetime.today().strftime(date_format),
                                                  MaxDate = (datetime.today() + timedelta(days=365*2)).strftime(date_format),
                                                  DayHours = [{
                                                      "Date": converted_vto_start_time.date().strftime(date_format),
                                                      "Count": None,
                                                      "Value": 1,
                                                      "Description": None,
                                                      "Id": 0,
                                                      "Title": None
                                                      }]
                                                  )
        
        # Validate leave request by calculating & checking daily hours...
        # response_check_daily_hours = tw_connector.request("PUT","/api/leave/checkdailyhours",tw_leave_request.to_json())
        # tw_leave_request = tw_leave_request.from_json(response_check_daily_hours)
        
        # Calculate the daily hours of a leave request
        response = tw_connector.request(request_method = "PUT",
                                        endpoint = "/api/leave/calcdailyhours/",
                                        payload = tw_leave_request.to_json())
        day_hours_obj = [{"DayHours": response.json()}]
        
        tw_leave_request.from_json(json.dumps(day_hours_obj))
        
        # Submit a leave request!
        print(json.loads(tw_leave_request.to_json()))
        leave_json_data = json.loads(tw_leave_request.to_json())
        final_response = tw_connector.request(request_method = "PUT",
                                        endpoint = f'/api/leave/post/{tw_employee[0]["Id"]}',
                                        payload = json.dumps(leave_json_data),
                                        params = {"validatedOnServer":"false"})
        
        if final_response.status_code == 409:
            ack({
                "response_action": "errors",
                "errors": {
                    "vto_start_time_input": "Conflicted with other request, Try again.",
                    "vto_end_time_input": "Conflicted with other request, Try again."
                }
            })
            return
        elif final_response.status_code == 200:
            user_name = user["user"]["profile"]["display_name"]
            ack({"response_action": "clear"})
            
            # Call the chat_postMessage or chat_postEphemeral
            if (user_id == message_mention):
                response = client.chat_delete(channel=channel_id,ts=message_ts)
            response = client.chat_postMessage(
                #user=user_id,
                username="Success",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"VTO Submission from <@{user_id}> completed:\
                            \n*VTO Start Time:* \n{vto_start_time_dt.strftime('%A, %B %d %Y %I:%M%p')}\
                            \n*VTO End Time:* \n{vto_end_time_dt.strftime('%A, %B %d %Y %I:%M%p')}"
                        }
                    }],
                    icon_url="https://convorelay.com/wp-content/uploads/2023/01/convo_bot_success_512.png",
                    thread_ts=f"{thread_ts}",
                    channel=f"{channel_id}",
                    text=f"VTO Submission from <@{user_id}> completed:\nVTO Start Time:\n{vto_start_time_dt.strftime('%A, %B %d %Y %I:%M%p')}\nVTO End Time: \n{vto_end_time_dt.strftime('%A, %B %d %Y %I:%M%p')}"
            )
            print(response)
            return

@app.shortcut("leave-request-shortcut")
def open_modal(ack: Ack, body: dict, client: WebClient):
    pass

###################################
#@app.event("workflow_step_completed")
#def complete(ack: Ack, body: dict, client: WebClient, workflow_step):
#    print('--------------- workflow_step_completed ---------------')
#    ack()
#    logging.info(body)



###################################
############# workflow_step_execute
###################################
@app.event("workflow_step_execute")
def execute(ack: Ack, body: dict, respond: Respond, client: WebClient):
    print('--------------- workflow_step_execute ---------------')
    ack()
    logging.info(body)
    
    step = body["event"]["workflow_step"]
    #completion = client.api_call(
    #    api_method="workflows.stepCompleted",
    #    json = {
    #        "workflow_step_execute_id": step["workflow_step_execute_id"],
    #        "outputs": {
    #            "vtoFormReceipient": step["inputs"]["vtoFormReceipient"]["value"],
    #           "vtoChannelSource": step["inputs"]["vtoChannelSource"]["value"],
    #            "vtoMessageLink": step["inputs"]["vtoMessageLink"]["value"],
    #        },
    #    },
    #)

    vto_form_receipient = step["inputs"]["vtoFormReceipient"]["value"]
    vto_channel_source = re.sub('[^A-Za-z0-9]+', '', step["inputs"]["vtoChannelSource"]["value"])
    vto_message_link = step["inputs"]["vtoMessageLink"]["value"]
    
    parsed_url = urlparse(vto_message_link)
    msg_path = parsed_url.path
    raw_msg_id = re.sub('\D','',os.path.split(msg_path)[-1])
    message_id = raw_msg_id[:-6] + "." + raw_msg_id[-6:]
    
    user = client.users_lookupByEmail(email=vto_form_receipient)
    vto_user_id = user["user"]["id"]
    
    # Call the chat_postMessage or chat_postEphemeral
    response = client.chat_postMessage(
        #user=f"{vto_user_id}",
        channel=f"{vto_channel_source}",
        text="Click button to open a leave request form.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Hello <@{vto_user_id}>!\nTo submit your VTO, Please fill out this form."
                }
            },
            {
                "type": "actions",
                "block_id": f"{message_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open VTO form",
                            "emoji": True
                        },
                        "value": "open-leave-request-form",
                        "action_id": "open-leave-request-form"
                    }
                ]
            }
        ],
        username="Teamwork Bot",
        icon_url="https://drive.google.com/file/d/10sWFW8BDAVGVzX7Jk-J7mxeCVCn49e2p",
        thread_ts=f"{message_id}"
    )

SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)

#def handler(event, context):
#    slack_handler = SlackRequestHandler(app=app)
#    return slack_handler.handle(event, context)

# Start teamwork integration slack app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))