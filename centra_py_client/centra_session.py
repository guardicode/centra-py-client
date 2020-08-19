import datetime
import json
import logging
from typing import Dict, Union
from urllib.parse import urljoin

from centra_py_client.exceptions import ManagementAPIError, ManagementAPITimeoutError, RESTAuthenticationError

import requests
from requests.auth import AuthBase

MANAGEMENT_REST_API_PORT = 443
AUTHENTICATION_ERROR_HTTP_STATUS_CODE = 403
TIME_FORMAT_STRING = "%Y/%m/%d %H:%M:%S.%f"  # this should be parsable by dateutil.parser
REST_API_BASE_PATH_V3 = '/api/v3.0/'


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(TIME_FORMAT_STRING)
            # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class JWTAuth(AuthBase):
    """Attaches JWT Authentication to the given Request object."""

    def __init__(self, token):
        # setup any auth-related data here
        if token is None:
            raise ManagementAPIError("REST Token not set!")
        self.token = token

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = 'Bearer ' + self.token
        return r


class CentraSession:
    def __init__(
        self,
        management_address: str,
        auth_username: str,
        auth_password: str,
        base_api_path=REST_API_BASE_PATH_V3,
        verify_certificate: bool = True
    ):
        """
        Todo
        :param management_address:
        :param auth_username:
        :param auth_password:
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.management_address = management_address
        self.auth_username = auth_username
        self.auth_password = auth_password

        self.http_server_root = f"https://{management_address}"
        self._requests_session = requests.Session()
        self._requests_session.verify = verify_certificate

        self.json_encoder = DatetimeEncoder()
        self.rest_auth_enabled = True
        self.authentication_handler = self.rest_authenticate

        self.set_base_api_path(base_api_path)

        self.connect()
        self.logger.debug(f"Connected to Centra successfully on {self.management_address}.")

    def set_base_api_path(self, base_api_path):
        # TODO import validators and validate the path
        self.base_api_path = base_api_path

    def urljoin_api(self, endpoint_path: str):
        return urljoin(self.base_api_path, endpoint_path)

    def rest_authenticate(self, rest_username, rest_password):
        """
        Perform JWT authentication through management REST API with username/password
        :param rest_username:
        :param rest_password:
        """
        self.logger.debug("REST Authenticating")
        response = self.json_query(uri=self.urljoin_api('authenticate'),
                                   method='POST',
                                   data={'username': rest_username, 'password': rest_password},
                                   authenticate=False)
        if 'access_token' in response:
            token = response['access_token']
            self.set_token(token)
        # todo raise exception when auth fails
        self.logger.debug("REST token obtained and set")

    def json_query(self,
                   uri,
                   method="GET",
                   data=None,
                   return_json=True,
                   params=None,
                   authenticate=True,
                   files=None,
                   convert_data_to_json=True) -> Union[bytes, Dict, str, None]:
        # TODO apijoin the uri
        if data is not None and convert_data_to_json:
            data = self.json_encoder.encode(data)
        response = self._query(uri=uri, method=method, data=data,
                               params=params, authenticate=authenticate, files=files)
        try:
            if not return_json:
                return response.content
            try:
                json_obj = json.loads(response.content)
            except TypeError:
                json_obj = json.loads(response.content.decode('utf-8'))
            if json_obj is not None and "code" in json_obj and 0 != json_obj["code"]:
                raise ManagementAPIError("Error: %s" % (json_obj["message"],))

            return json_obj
        except ValueError as exc:
            raise ManagementAPIError("Error reading server response: %s :: [%s]" % (str(exc), response.content))

    def _query(self, uri, method="GET", data=None, params=None, authenticate=True, files=None, **kwargs):
        if params is None:
            params = {}

        self.logger.debug("%s %s%s", method, uri, ('' if not params
                                                   else '?' + '&'.join("%s=%s" % (key, value)
                                                                       for key, value in params.items())))

        method_func = {"GET": self._requests_session.get,
                       "POST": self._requests_session.post,
                       "PUT": self._requests_session.put,
                       "PATCH": self._requests_session.patch,
                       "DELETE": self._requests_session.delete}[method]

        headers = {'content-type': 'application/json'} if files is None else None
        auth = JWTAuth(self.token) if (authenticate and self.rest_auth_enabled) else None
        # print urljoin(self.http_server_root, uri), data, headers, params
        try:
            r = method_func(urljoin(self.http_server_root, uri), data=data, headers=headers,
                            params=params, auth=auth, files=files, **kwargs)
        except requests.exceptions.RequestException as e:
            raise ManagementAPIError("Error while handling %s request for uri %s: %s" % (method, uri, e))

        if AUTHENTICATION_ERROR_HTTP_STATUS_CODE == r.status_code:  # This is a potential authorization error
            raise RESTAuthenticationError(r)

        if 200 != r.status_code:
            try:
                json_obj = json.loads(r.content)
            except:  # noqa: E722
                json_obj = r.content
                if isinstance(json_obj, bytes) and b"504 Gateway Time-out" in json_obj:
                    raise ManagementAPITimeoutError(json_obj)

            raise ManagementAPIError(json_obj)

        return r

    def connect(self):
        self.authentication_handler(self.auth_username, self.auth_password)

    def disconnect(self):
        self.json_query(self.urljoin_api('logout'), method='POST', return_json=False)

    def set_token(self, token):
        """
        Set JWT token, used for authentication with REST API
        :param token:
        """
        self.logger.debug("Setting REST token")
        self.token = token
        self._requests_session.auth = JWTAuth(self.token)  # so others can use this session
