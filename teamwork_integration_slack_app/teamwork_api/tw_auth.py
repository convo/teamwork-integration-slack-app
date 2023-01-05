from dataclasses import dataclass, field, asdict
from datetime import datetime
import os
import json
import requests
from requests import exceptions
from dotenv import load_dotenv
load_dotenv()

# Convert a data class instance into a json object
def to_json(data_instance):
    return json.dumps(data_instance.__dict__)

@dataclass
class Employee(object):
    id: int = 0
    email: str = None
    full_name: str = None
    employee_number: str = None
    full_name: str = None
    location_name: str = None
    
    def __post_init__(self):
        print('Initialized creating an employee object...')
    
@dataclass
class Employee_Leave_Request(object):
    Id: int = 0
    Start: datetime = None
    End: datetime = None
    Days: int = 0
    StartTime: datetime = None
    EndTime: datetime = None
    TypeId: int = 544
    TypeName: str = ""
    Conflicts: int = 0
    Hours: int = 0
    CalculatedHours: int = 0
    Balance: str = ""
    Status: int = 1
    StatusText: str = ""
    StatusDisplay: str = ""
    TimeHours: int = 0
    TimeTaskId: int = 0
    EmpId: int = 0
    EmpName: str = ""
    Notes: str = ""
    Employees: list = field(default_factory=lambda : [])
    LeaveTypes: list = field(default_factory=lambda : [])
    AccrualBalances: list = field(default_factory=lambda : [])
    MinDate: datetime = None
    MaxDate: datetime = None
    MaxDays: int = 0
    MaxHours: int = 0
    SaveEntered: bool = False
    CanEdit: bool = True
    CanCancel: bool = False
    CanDelete: bool = True
    CanRemoveCancel: bool = False
    BalanceIsDays: bool = False
    OverBalance: bool = False
    CommentRequired: bool = False
    IsLeaveManagement: bool = False
    IsAllDay: bool = False
    Created: datetime = None
    CanGrant: bool = True
    CanRequest: bool = False
    CanDeny: bool = True
    HasPolicy: bool = True
    Messages: str = ""
    QuotaCheck: str = ""
    LimitCheck: str = ""
    Styles: list = field(default_factory=lambda : [])
    DayHours: list = field(default_factory=lambda : [])
    
    def from_json(self, json_data):
        data = json.loads(json_data)
        print(data)
        for d in data:
            for key, value in d.items():
                setattr(self, key, value)
    
    def to_json(self):
        return json.dumps(self.__dict__)
    
    def __post_init__(self):
        print('Initialized making a leave request object...')
    
    
    
@dataclass
class TW_Connector(object):
    base_url: str
    portal: str
    code: str
    username: str
    password: str
    session_id: str = None
    api_token: str = None
    
    def get_employee_by_email(self, email):
        if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
        not self.api_token and not self.session_id:
            self._authenicate_tw()
        url = self.base_url + "/api/employees/list"
        print(url)
        print(self.headers)
        response = requests.get(url = url,
                                headers=json.loads(self.headers),
                                params= {
                                    "sort":"",
                                    "page":"1",
                                    "pageSize":"10",
                                    "group":"",
                                    "filter":f"Email~contains~'{email}'"
                                })
        
        response.raise_for_status()
        result = response.json()
        print(result)
        return response
        #return result['Data']
    
    def get(self, endpoint, **kwargs):
        if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                not self.api_token and not self.session_id:
            self._authenicate_tw()
        
        response = requests.get(url = f"{self.base_url}" + endpoint,
                                headers=json.loads(self.headers),
                                **kwargs)
        
        #response.raise_for_status()
        #result = response.json()
        return response
    
    def post(self, endpoint, payload, **kwargs):
        if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                not self.api_token and not self.session_id:
            self._authenicate_tw()
            
        response = requests.post(url = f"{self.base_url}" + endpoint,
                                json = payload,
                                headers = json.loads(self.headers),
                                **kwargs)
        
        response.raise_for_status()
        response.status_code
        return response
        #result = response.json()
        #print(result)
    
    def request(self, request_method, endpoint, payload, **kwargs):
        try:
            if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                    not self.api_token and not self.session_id:
                self._authenicate_tw()
                
            response = requests.request(method = request_method,
                                        url = f"{self.base_url}" + endpoint,
                                        data = payload,
                                        headers = json.loads(self.headers),
                                        **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            print(f'--- Http Error:\n {e}\n---')
            return response
    def _authenicate_tw(self):
        # uses standard creds to authenticate via the API
        # Endpoint (verb = POST): <baseURL>/api/ops/auth

        payload_data = json.dumps(
            {
            "Request": {
                "Portal": self.portal,
                "Code": self.code,
                "Username": self.username,
                "Password": self.password
                }
        }
            )
        
        response = requests.post(
                            url = f'{self.base_url}/api/ops/auth',
                            data = payload_data,
                            headers = {"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        
        # Check if the authentication is success
        if not result['Success']:
            raise Exception(f'Teamwork authentication unsuccessful, the response returned: \n{result}\n')
        else:
            self.session_id = result['Response']['SessionId']
            self.api_token = result['Response']['APIToken']
            self.headers = json.dumps({
                "x-session-id": f"{self.session_id}",
                "x-api-token": f"{self.api_token}",
                "Content-Type": "application/json"
            })
        
    def __post_init__(self):
        
        print('Initialized Teamwork integration connection.')
        
        if not self.portal == '' and not self.code == '' \
            and not self.username == '' and not self.password == '' \
            and not self.base_url == '':
            
            print('Authentication credientials detected. It is ready to connect to Teamwork via API.')
        else:
            print('Blank credentials detected! Please fill in the required credentials for authenicating Teamwork via API.')