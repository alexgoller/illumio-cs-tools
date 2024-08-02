import json
import base64
import time
from typing import Any, List, Union
from requests import Session, Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .secpolicy import PolicyChangeset, PolicyVersion
from .exceptions import IllumioApiException
from .policyobjects import IPList, Service
from .util import (
    deprecated,
    convert_active_href_to_draft,
    parse_url,
    href_from,
    validate_int,
    islist,
    Reference,
    IllumioEncoder,
    ACTIVE,
    DRAFT,
    PORT_MAX,
    ANY_IP_LIST_NAME,
    ALL_SERVICES_NAME,
    BULK_CHANGE_LIMIT,
    PCE_APIS
)

class IllumioApiException(Exception):
    pass

def parse_url(url):
    scheme, hostname = url.split('://')
    return scheme, hostname

def validate_int(value, minimum, maximum=None):
    value = int(value)
    if value < minimum or (maximum and value > maximum):
        raise ValueError(f"Value {value} out of range ({minimum}-{maximum})")
    return value

def islist(value):
    return isinstance(value, list)

class Reference:
    @staticmethod
    def from_json(data):
        return Reference(**data)

class IllumioEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__

class CloudSecureClient:
    def __init__(self, url: str, tenant_id: str, service_account_key: str, service_account_token: str, port: str = '443', version: str = 'v1', retry_count: int = 5, request_timeout: int = 30) -> None:
        self._apis = {}
        self._session = Session()
        self._session.headers.update({'Accept': 'application/json'})
        self._scheme, self._hostname = parse_url(url)
        self._port = port
        self._version = version
        self._timeout = request_timeout
        self._tenant_id = tenant_id
        self._encoder = IllumioEncoder()
        self.base_url = "{}://{}:{}/api/{}".format(self._scheme, self._hostname, port, version)
        self._setup_retry(retry_count)
        self._set_auth_headers(service_account_key, service_account_token)

    def _setup_retry(self, retries: int) -> None:
        retry_strategy = Retry(
            total=retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _set_auth_headers(self, service_account_key: str, service_account_token: str):
        auth = ':'.join([service_account_key, service_account_token])
        auth_base64 = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        self._session.headers.update({
            'Authorization': f'Basic {auth_base64}',
            'Content-Type': 'application/json',
            'X-Tenant-Id': self._tenant_id
        })

    def set_credentials(self, service_account_key: str, service_account_token: str) -> None:
        self._set_auth_headers(service_account_key, service_account_token)

    def _request(self, method: str, endpoint: str, **kwargs) -> Response:
        try:
            response = None
            url = self._build_url(endpoint)
            self._encode_body(kwargs)
            kwargs['timeout'] = kwargs.get('timeout', self._timeout)
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            message = str(e)
            if response is not None:
                if response.headers.get('Content-Type', '') == 'application/json':
                    message = self._get_error_message_from_response(response)
            raise IllumioApiException(message) from e

    def _build_url(self, endpoint: str):
        endpoint = endpoint.lstrip('/').replace('//', '/')
        return '{}://{}:{}/api/{}/{}'.format(
            self._scheme, self._hostname, self._port, self._version, endpoint
        )

    def _encode_body(self, kwargs):
        body = kwargs.pop('data', None)
        if 'json' in kwargs:
            body = kwargs.pop('json')
        if body is not None:
            kwargs['json'] = json.loads(self._encoder.encode(body))

    def _get_error_message_from_response(self, response: Response) -> str:
        message = "API call returned error code {}. Errors:".format(response.status_code)
        error_response = response.json()
        if islist(type(error_response)):
            for error in error_response:
                if error and 'token' in error and 'message' in error:
                    message += '\n{}: {}'.format(error['token'], error['message'])
                elif error and 'error' in error:
                    message += '\n{}'.format(error['error'])
                else:
                    message += '\n{}'.format(error)
        else:
            message += '\n{}'.format(error_response)
        return message

    def get(self, endpoint: str, **kwargs) -> Response:
        return self._request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Response:
        headers = kwargs.get('headers', {})
        kwargs['headers'] = {**headers, **{'Content-Type': 'application/json'}}
        return self._request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Response:
        headers = kwargs.get('headers', {})
        kwargs['headers'] = {**headers, **{'Content-Type': 'application/json'}}
        return self._request('PUT', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Response:
        return self._request('DELETE', endpoint, **kwargs)

    def get_collection(self, endpoint: str, **kwargs) -> Response:
        try:
            headers = kwargs.get('headers', {})
            kwargs['headers'] = {**headers, **{'Prefer': 'respond-async'}}
            response = self.get(endpoint, **kwargs)
            response.raise_for_status()
            location = response.headers['Location']
            retry_after = int(response.headers['Retry-After'])
            collection_href = self._async_poll(location, retry_after)
            response = self.get(collection_href)
            response.raise_for_status()
            return response
        except Exception as e:
            raise IllumioApiException from e

    def _async_poll(self, job_location: str, retry_time: Union[int, float] = 1.) -> str:
        while True:
            time.sleep(retry_time)
            retry_time *= 1.5
            response = self.get(job_location)
            response.raise_for_status()
            poll_result = response.json()
            poll_status = poll_result['status']
            if poll_status == 'failed':
                raise Exception('Async collection job failed: ' + poll_result['result']['message'])
            elif poll_status == 'completed':
                collection_href = poll_result['result']
                break
            elif poll_status == 'done':
                collection_href = poll_result['result']['href']
                break
        return collection_href

    def must_connect(self, **kwargs) -> None:
        self._check_connection(**kwargs)

    def check_connection(self, **kwargs) -> bool:
        try:
            self._check_connection(**kwargs)
            return True
        except IllumioApiException:
            return False

    def _check_connection(self, **kwargs):
        self.get('/health', **kwargs)

    class _CloudSecureObjectAPI:
        def __init__(self, client: 'CloudSecureClient', api_data: object) -> None:
            self.name = api_data.name
            self.endpoint = api_data.endpoint
            self.object_cls = api_data.object_class
            self.is_sec_policy = api_data.is_sec_policy
            self.is_global = api_data.is_global
            self.client = client

        def get(self, **kwargs) -> List[Reference]:
            print(**kwargs)
            endpoint = self.endpoint
            response = self.client.get(endpoint, **kwargs)
            if islist(type(response.json())):
                return [self.object_cls.from_json(o) for o in response.json()]
            elif type(response.json()) is dict:
                return self.object_cls.from_json(response.json())
            return response.json()

        def get_all(self, **kwargs) -> List[Reference]:
            params = kwargs.get('params', {})
            endpoint = self.endpoint
            if 'max_results' not in params:
                kwargs['params'] = {**params, **{'max_results': 0}}
                response = self.client.get(endpoint, **kwargs)
                if len(response.json()) > 0:
                    return [self.object_cls.from_json(o) for o in response.json()]
                filtered_object_count = response.headers['X-Total-Count']
                kwargs['params'] = {**params, **{'max_results': int(filtered_object_count)}}
            response = self.client.get(endpoint, **kwargs)
            return [self.object_cls.from_json(o) for o in response.json()]

        def create(self, body: Any, **kwargs) -> Reference:
            kwargs = {**kwargs, **{'json': body}}
            print(self.is_sec_policy)
            endpoint = self._build_endpoint(DRAFT, None)
            response = self.client.post(endpoint, **kwargs)
            return self._parse_response_body(response.json())

        def _build_endpoint(self, policy_version: str, parent: Any) -> str:
            """Builds the CloudSecure request endpoint."""
            endpoint = self.endpoint

            if self.is_sec_policy:
                if policy_version not in [ACTIVE, DRAFT]:
                    raise IllumioApiException("Invalid policy_version passed to get: {}".format(policy_version))
                endpoint = '/sec_policy/{}/{}'.format(policy_version, endpoint)

            return endpoint.replace('//', '/')


        def _parse_response_body(self, json_response):
            if type(json_response) is list:
                results = {self.name: [], 'errors': []}
                for o in json_response:
                    if 'href' in o:
                        results[self.name].append(self.object_cls.from_json(o))
                    else:
                        results['errors'].append(o)
                return results
            return self.object_cls.from_json(json_response)

        def update(self, reference: Union[str, Reference, dict], body: Any, **kwargs) -> None:
            kwargs['json'] = body
            self.client.put(reference, **kwargs)

        def delete(self, reference: Union[str, Reference, dict], **kwargs) -> None:
            self.client.delete(reference, **kwargs)

    def __getattr__(self, name: str) -> _CloudSecureObjectAPI:
        """Instantiates a generic API for registered PCE objects.

        Inspired by the Zabbix API: https://pypi.org/project/zabbix-api/
        """
        print(name)
        if name in self._apis:
            return self._apis[name]
        if name not in PCE_APIS:
            raise AttributeError("No such PCE API object: {}".format(name))
        api = self._CloudSecureObjectAPI(client=self, api_data=PCE_APIS[name])
        self._apis[name] = api
        return api
