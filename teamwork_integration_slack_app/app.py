import os
import logging
from slack_sdk import WebClient
from slack_sdk.web import SlackResponse

from slack_bolt.authorization import AuthorizeResult
from slack_bolt import App, Ack
from slack_bolt.workflows.step import WorkflowStep

from teamwork_api.tw_auth import TW_Connector,Employee_LeaveRequest
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

# Initializes app with bot token and signing secret
def authorize(client: WebClient):
    
    token = os.environ["SLACK_BOT_TOKEN"]
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    
    return AuthorizeResult.from_auth_test_response(
        auth_test_response=client.auth_test(token=token),
        bot_token=token,
    )
    
app = App(signing_secret = os.environ["SLACK_SIGNING_SECRET"],
          token = os.environ["SLACK_BOT_TOKEN"],
          authorize=authorize)
   
 
@app.action({'type': 'workflow_step_edit', 'callback_id': 'leave_request'})
def edit(body: dict, ack: Ack, client: WebClient):
    
    ack()
    
    new_modal: SlackResponse = client.views_open(
        trigger_id = body['trigger_id'],
        view = {}
    )


@app.view('leave_request_view')
def save(ack: Ack, client: WebClient, body: dict):
    
    state_values = body["view"]["state"]["values"]
    
    response: SlackResponse = client.api_call(
        api_method = 'workflows.updateStep',
        json = {
            'workflow_step_edit_id': body['workflow_step']['workflow_step_edit_id'],
            'inputs': {
                # VTO Start Time input
                {
                    'vtoStartTime': state_values['vto_start_time_input']['vto_start_time']['value'],
                },
                # VTO End Time input
                {
                    'vtoEndTime': state_values['vto_end_time_input']['vit_end_time']['value'], 
                },
                # Timezone input
                {
                    'vtoTimezone': state_values['vto_timezone_input']['timezone']['value'],
                },
                # User's email input
                {
                    'vtoRequestUser': state_values['vto_request_user_input']['vto_request_user']['value'],
                },
            },
            'outputs': [
                {
                    'name': 'vtoStartTime',
                    'type': 'timestamp',
                    'label': 'VTO Start Time'
                },
                {
                    'name': 'vtoEndTime',
                    'type': 'timestamp',
                    'label': 'VTO End Time'
                },
                {
                    'name': 'vtoTimezone',
                    'type': 'text',
                    'label': 'Timezone'
                },
                {
                    'name': 'vtoRequestUser',
                    'type': 'text',
                    'label': 'Timezone'
                },
            ]
        }
    )
    ack()


@app.event("workflow_step_execute")
def execute(body: dict, client: WebClient):
    
    step = body['event']['workflow_step']
    
    completion: SlackResponse = client.api_call(
        api_method='workflows.stepCompleted',
        json = {
            'workflow_step_execute_id': step['workflow_step_execute_id'],
            'outputs': {
                'vtoStartTime': step['inputs']['vtoStartTime']['value'],
                'vtoEndTime': step['inputs']['vtoEndTime']['value'],
                'vtoTimezone': step['inputs']['vtoTimezone']['value'],
                'vtoRequestUser': step['inputs']['vtoRequestUser']['value'],
                
            },
        },
    )
    
    user: SlackResponse = client.users_lookupByEmail(email=step["inputs"]["vtoRequestUser"]["value"])
    
    user_id = user['user']['id']
    timezone = user['user']['tz']
    timezone_label = user['user']['tz_label']
    user_email = user['user']['profile']['email']
    
    tw_connector = TW_Connector(base_url = os.environ.get('TEAMWORK_URL'),
                                portal = os.environ.get('TEAMWORK_PORTAL'),
                                code = os.environ.get('TEAMWORK_CODE'),
                                username = os.environ.get('TEAMWORK_USERNAME'),
                                password = os.environ.get('TEAMWORK_PASSWORD'))
    tw_connector._authenicate_tw()
    
    # Find the employee information by email
    tw_employee = tw_connector.get_employee_by_email(user_email)
    print('--- Employee Information')
    print(tw_employee)
    print('---')
    # Get the list of leave types
    tw_leave_types = tw_connector.get('/api/leave/leavetypes')
    
    print('--- List of Teamwork\'s Leave Types')
    print(tw_leave_types)
    print('---')
    
    if not len(tw_leave_types) == 0:
        for i in len(tw_leave_types['data']):
            if i['data']['Title'] == 'VTO: Slack' or i['data']['Code'] == 'VTOSLACK':
                selected_leave_type = i['data']
    
    print('--- Selected VTO Slack type')
    print(selected_leave_type)
    print('---')
    
    # Initialize a leave request
    tw_leave_request = Employee_LeaveRequest(EmpId = tw_employee['Data'][0]['Id'],
                                             EmpName = tw_employee['Data'][0]['FullName'],
                                             Employees = [{'Id': tw_employee['Data'][0]['Id'],
                                                           'Title': tw_employee['Data'][0]['FullName']}])


# Start teamwork integration slack app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))