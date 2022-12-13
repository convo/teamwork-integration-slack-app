from dataclasses import dataclass, field, asdict
from datetime import datetime
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Employee(object):
    id: int = 0
    email: str = None
    full_name: str = None
    employee_number: str = None
    full_name: str = None
    location_name: str = None
    

@dataclass
class Employee_LeaveRequest(object):
    Id: int = None
    Start: datetime = None
    End: datetime = None
    Days: int = 0
    StartTime: datetime = None
    EndTime: datetime = None
    TypeId: int = 0
    TypeName: str = None
    Conflicts: int = 0
    Hours: int = 0
    CalculatedHours: int = 0
    Balance: str = 'N/A'
    Status: int = 0
    StatusText: str = None
    StatusDisplay: str = None
    TimeHours: int = 0
    TimeTaskId: int = 0
    EmpId: int = 0
    EmpName: str = None
    Notes: str = None
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
    CanDelete: bool = False
    CanRemoveCancel: bool = False
    BalanceIsDays: bool = False
    OverBalance: bool = False
    CommentRequired: bool = False
    IsLeaveManagement: bool = False
    IsAllDay: bool = False
    Created: datetime = None
    CanGrant: bool = False
    CanRequest: bool = False
    CanDeny: bool = False
    HasPolicy: bool = True
    Messages: str = None
    QuotaCheck: str = None
    LimitCheck: str = None
    Styles: str = None
    DayHours: list = field(default_factory=lambda : [])
    
    def __post_init__(self):
        print('Initialized making a leave request object...')
        
    def _calc_daily_hours(self, object):
        pass
    
    def _check_daily_hours(self, object):
        pass
    
    
    
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
        attempts = 0
        while attempts < 3:
            try:
                
                if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                not self.api_token and not self.session_id:
                    self._authenicate_tw()
                
                response = requests.get(url = self.base_url + "/api/employees/list",
                                        headers=self.headers,
                                        params= {
                                            'sort':'',
                                            'page':'1',
                                            'group':'',
                                            'filter':f'Email~contains~\'{email}\''
                                        })
                
                response.raise_for_status()
                result = response.json()
                
                if result['data'] == 'Session Timeout. Please sign in again.':
                    raise TimeoutError
                else:
                    if len(result['data']) == 0:
                        print(f'ERROR: We couldn\'t find an employee by the following email: {email}')
                        return None
                    break
                
            except requests.exceptions.TimeoutError as e:
                attempts += 1
                print('ERROR: Ah no, the session has expired! Reconnecting Teamwork...')
                self.api_token = ''
                self.session_id = ''
                continue
        
        return result['data']
    
    def get(self, endpoint, **kwargs):
        attempts = 0
        while attempts < 3:
            try:
                if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                        not self.api_token and not self.session_id:
                    self._authenicate_tw()
                
                response = requests.get(url = f"{self.base_url}" + endpoint,
                                        headers=self.headers,
                                        **kwargs)
                
                response.raise_for_status()
                result = response.json()
                
                if result['data'] == 'Session Timeout. Please sign in again.':
                    raise TimeoutError
                break
            
            except requests.exceptions.TimeoutError as e:
                attempts += 1
                print('ERROR: Ah no, the session has timed out! Reconnecting Teamwork...')
                self.api_token = ''
                self.session_id = ''
                continue
        return result
    
    def post(self, endpoint, payload, **kwargs):
        attempts = 0
        while attempts < 3:
            try:
                if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                        not self.api_token and not self.session_id:
                    self._authenicate_tw()
                    
                response = requests.post(url = f"{self.base_url}" + endpoint,
                                        json = payload,
                                        headers = self.headers,
                                        **kwargs)
                
                response.raise_for_status()
                result = response.json()
                
                if result['data'] == 'Session Timeout. Please sign in again.':
                    raise TimeoutError
                break
            
            except requests.exceptions.TimeoutError as e:
                attempts += 1
                print('ERROR: Ah no, the session has timed out! Reconnecting Teamwork...')
                self.api_token = ''
                self.session_id = ''
                continue
        return result
    
    def request(self, request_method, endpoint, payload, **kwargs):
        attempts = 0
        while attempts < 3:
            try:
                if not hasattr(self, 'api_token') and not hasattr(self, 'session_id') or \
                        not self.api_token and not self.session_id:
                    self._authenicate_tw()
                    
                response = requests.request(method = request_method,
                                            url = f"{self.base_url}" + endpoint,
                                            json = payload,
                                            headers = self.headers,
                                            **kwargs)
                
                response.raise_for_status()
                result = response.json()
                
                if result['data'] == 'Session Timeout. Please sign in again.':
                    raise TimeoutError
                break
            
            except requests.exceptions.TimeoutError as e:
                attempts += 1
                print('ERROR: Ah no, the session has timed out! Reconnecting Teamwork...')
                self.api_token = ''
                self.session_id = ''
                continue
        return result
    
    def _authenicate_tw(self):
        # uses standard creds to authenticate via the API
        # Endpoint (verb = POST): <baseURL>/api/ops/auth

        payload_data = json.dumps({
        "Request": {
            "Portal": self.portal,
            "Code": self.code,
            "Username": self.username,
            "Password": self.password
            }
        })
        
        response = requests.post(
                            url = f'{self.base_url}/api/ops/auth',
                            json = payload_data,
                            headers = {'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        result = response.json()
        
        # Check if the authentication is success
        if not result['Success']:
            raise Exception(f'Teamwork authentication unsuccessful, the response returned: \n{result}\n')
        else:
            self.session_id = result['SessionId']
            self.api_token = result['APIToken']
            self.headers = json.dumps({
                "Content-Type": "application/json",
                "x-session-id": f"{self.session_id}",
                "x-api-token": f"{self.api_token}"
            })
        
    def __post_init__(self):
        
        print('Initialized Teamwork integration connection.')
        
        if not self.portal == '' and not self.code == '' \
            and not self.username == '' and not self.password == '' \
            and not self.base_url == '':
            
            print('Authentication credientials detected. It is ready to connect to Teamwork via API.')
        else:
            print('Blank credentials detected! Please fill in the required credentials for authenicating Teamwork via API.')