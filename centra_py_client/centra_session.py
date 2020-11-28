import logging
import math
import requests

from functools import wraps
from urllib.parse import urljoin
from typing import Dict, Union, Callable, Generator

from centra_py_client.exceptions.session import CentraAPIError, CentraAPIRequestTimeout, CentraAuthError, \
    BadAPIRequest, CentraAPIBaseError, NoPermissionToAccessResource, RedirectionRequiredError

MANAGEMENT_REST_API_PORT = 443
REST_API_BASE_PATH_V3 = 'api/v3.0/'

logger = logging.getLogger('guardicore.CentraSession')


def rest_auto_reconnect(f):
    """
    Decorator that enables re authentication to Centra in case CentraAuthError was raised, which might indicate the
    API access token is expired.
    Re authentication will only be performed in case the last authentication attempt was successful.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except CentraAuthError as e:
            if not self.last_rest_auth_attempt_was_successful or not self.rest_auto_reconnect:
                # Either this is an authentication request which failed or auto reconnect is False
                raise

            self.logger.error(e)
            self.last_rest_auth_attempt_was_successful = False
            self.logger.info("Token might have expired; re-authenticating")
            self.login()
            return f(self, *args, **kwargs)
    return wrapper


def logging_hook(response, *args, **kwargs) -> None:
    """ Log the content of query response from Centra """
    if response.headers.get('content-type') == 'application/json':
        try:
            logger.debug(response.json())
        except ValueError:
            logger.debug(response.content.decode('utf-8'))
    else:
        logger.debug(response.content.decode('utf-8'))


def assert_status_hook(response: requests.Response, *args, **kwargs) -> None:
    """ Validate a response from Centra API and raise the appropriate exception in case of an error """
    if response.ok:
        return

    if response.headers.get("Content-Type") == "application/json":
        data = response.json()
        if response.status_code == 401:
            raise CentraAuthError(f'{data["error"]}: {data["description"]}')
        elif response.status_code == 403:
            raise NoPermissionToAccessResource(f'{data["error"]}: {data["description"]}')
        else:
            raise CentraAPIError(f'{data["error"]}: {data["description"]}')
    else:
        if response.status_code == 504:
            raise CentraAPIRequestTimeout("The request timed out")
        elif response.status_code == 404:
            raise BadAPIRequest("The requested URL was not found")
        elif response.status_code == 406:
            pass  # handled by CentraSession._query to allow following location redirection
        else:
            response.raise_for_status()


def ask_for_2fa_code(username: str) -> str:
    """ Prompt the user for 2fa code """
    return input(f"Please supply 2fa access code for user {username}: ")


class WrappedSession(requests.Session):
    """
    A wrapper for requests.Session to override 'verify' property, ignoring REQUESTS_CA_BUNDLE environment variable.
    This is a workaround for https://github.com/kennethreitz/requests/issues/3829 (will be fixed in requests 3.0.0)
    """

    def merge_environment_settings(self, url, proxies, stream, verify, *args, **kwargs):
        if self.verify is False:
            verify = False

        return super().merge_environment_settings(url, proxies, stream, verify, *args, **kwargs)


class CentraSession:
    def __init__(
        self,
        management_address: str,
        auth_username: str,
        auth_password: str = None,
        allow_two_factor_auth: bool = False,
        two_factor_auth_callback: Callable = None,
        management_api_port: int = MANAGEMENT_REST_API_PORT,
        base_api_path: str = REST_API_BASE_PATH_V3,
        verify_certificate: bool = True,
        login: bool = True,
        auto_reconnect: bool = True,
        follow_redirects: bool = True,
        log_query_responses: bool = False
    ):
        """
        Centra API session object, providing authentication and querying functionality.
        :param management_address: The address of the management server UI and API
        :param auth_username: a name of a Centra user to authenticate with
        :param auth_password: Optional. Provide the password for the Centra user
        :param allow_two_factor_auth: Whether to allow two factor authentication if it is required for the provided user
        :param two_factor_auth_callback: A callback function for two factor authentication. The callback function should
        receive the provided username, and return a 2fa code for this user
        :param management_api_port: Override default API port
        :param base_api_path: Override default Centra api base path
        :param verify_certificate: Whether to validate Centra's certificate
        :param login: Whether to send a log in request to Centra API to obtain a token. Set to False to avoid
        authentication request on CentraSession creation.
        :param auto_reconnect: Whether to perform automatic reconnection to Centra when the session's token is expired
        :param follow_redirects: Whether to follow http redirects in API responses
        :param log_query_responses: If True, query responses from Centra will be logged at DEBUG level
        """
        self.logger = logging.getLogger("guardicore.CentraSession")

        self.management_address = management_address
        self.management_api_port = management_api_port
        self.base_api_path = base_api_path
        self.http_base_url = f'https://{self.management_address}:{self.management_api_port}/{self.base_api_path}'

        self._http = WrappedSession()
        self._http.verify = verify_certificate

        self._http.hooks["response"] = [assert_status_hook]
        if log_query_responses:
            self._http.hooks["response"].append(logging_hook)

        self._http_method_map = {"GET": self._http.get,
                                 "POST": self._http.post,
                                 "PUT": self._http.put,
                                 "PATCH": self._http.patch,
                                 "DELETE": self._http.delete,
                                 "HEAD": self._http.head}

        self.access_token = None
        self.auth_username = auth_username
        self.auth_password = auth_password
        self.allow_two_factor_auth = allow_two_factor_auth
        self.two_factor_auth_callback = two_factor_auth_callback
        self.two_factor_auth_is_required = None
        self.follow_redirects = follow_redirects

        self.rest_auto_reconnect = auto_reconnect
        self.last_rest_auth_attempt_was_successful = None

        if login:
            self.login()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @rest_auto_reconnect
    def _query(self,
               endpoint: str,
               method: str = "GET",
               params=None,
               data=None,
               files=None,
               **kwargs) -> requests.Response:
        """
        Send an HTTP request to Centra API.
        Most function parameters are sent as is to requests.Session.request(), except for the data parameter which is
        always sent as json.
        :param endpoint: Centra Rest API endpoint to query
        :param method: HTTP request method as uppercase string (e.g. GET, POST, PUT)
        :param params: HTTP request query parameters
        :param data: data to send as json in the body of the request
        :param files: files for multipart encoding upload
        :param kwargs: Additional arguments for requests.Session.request()
        :return: requests.Response object
        """
        if params is None:
            params = {}

        uri = self.get_api_request_uri(endpoint)

        self.logger.debug("%s %s%s", method, uri,
                          '' if not params else '?' + '&'.join(f"{key}={value}" for key, value in params.items()))
        try:
            method_func = self._http_method_map[method]
        except KeyError:
            raise BadAPIRequest(f"{method} is not a valid HTTP method. "
                                f"Must be one of {', '.join(self._http_method_map)}")

        headers = {'content-type': 'application/json'} if not files else None

        try:
            response = method_func(uri, params=params, json=data, headers=headers, files=files, **kwargs)
        except CentraAPIBaseError as e:
            raise type(e)(f"Error while handling {method} request for {uri}: {e}") from None
        except requests.exceptions.SSLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                raise CentraAuthError(
                    "Could not verify the validity of Centra's certificate. This might happen when connecting to "
                    "Centra using the management's IP or Centra has a self signed certificate. \n"
                    "To disable certificate validity check, provide the argument `verify_certificate=False` when "
                    "creating the CentraSession. \n"
                    "Note that setting `verify_certificate` to `False` will make your API connection "
                    "vulnerable to man-in-the-middle attacks, so this should be used only in a trusted environment.")
            else:
                raise

        if response.status_code == 406:
            if self.follow_redirects and 'Location' in response.headers:
                if response.headers['Location'].startswith(self.base_api_path):
                    redirect_target = response.headers['Location'][len(self.base_api_path):]
                else:
                    redirect_target = response.headers['Location']
                response = self._query(redirect_target, method=method, data=data, params=params, files=files, **kwargs)
            else:
                raise RedirectionRequiredError("HTTP 406 was returned from Centra. Either the request is bad or "
                                               "redirection is required but not allowed because `follow_redirects` "
                                               "is not `True`")

        return response

    def get_api_request_uri(self, endpoint: str) -> str:
        """ Format a request URI """
        return urljoin(self.http_base_url, endpoint)

    def query(self,
              endpoint: str,
              method: str = "GET",
              params=None,
              data=None,
              files=None,
              return_json: bool = True,
              **kwargs) -> Union[bytes, Dict, str, None]:
        """
        Send a request to Centra API and return the response.
        :param endpoint: Centra Rest API endpoint to query
        :param method: HTTP request method as uppercase string (e.g. GET, POST, PUT)
        :param params: HTTP request query parameters
        :param data: Data to send as json in the body of the request
        :param files: Files for multipart encoding upload
        :param return_json: Whether to returns the json-encoded content of the response
        :param kwargs: Additional arguments for requests.Session.request()
        :return: The response from Centra API
        """
        response = self._query(endpoint, method=method, data=data, params=params, files=files, **kwargs)
        try:
            if return_json:
                return response.json()
            else:
                return response.content
        except ValueError as e:
            raise CentraAPIBaseError(f"Error reading server response: {e} :: {response.content}")

    def login(self) -> None:
        """
        Log in to Centra API to obtain a session token.
        If two factor authentication is required and enabled, perform two factor authentication.
        """
        logger.debug(f"Performing authentication for {self.management_address} using the username {self.auth_username}")
        response = self.query("authenticate",
                              method="POST",
                              data={"username": self.auth_username, "password": self.auth_password})

        if "access_token" in response:
            access_token = response["access_token"]
        elif response.get("2fa_required"):
            if self.allow_two_factor_auth:
                self.logger.info("2FA Authentication is required")
                self.two_factor_auth_is_required = True
                access_token = self._perform_two_factor_authentication(response["2fa_temp_token"])
            else:
                raise CentraAuthError("2FA Authenticating is needed but not allowed")
        else:
            raise CentraAuthError(f"Unexpected response for authentication request: {response}")

        self.last_rest_auth_attempt_was_successful = True
        self.set_token(access_token)

    def _perform_two_factor_authentication(self, temp_token: str) -> str:
        """
        Perform two factor authentication for Centra API.
        If self.two_factor_auth_callback is defined, use the provided callback function to get the 2fa code.
        Otherwise, prompt the user for the 2fa code.
        :param temp_token: Temporary access token resulting from supplying correct username and password to the
        authenticate endpoint - the first step of the two factor authentication.
        :return: Centra access token
        """
        if self.two_factor_auth_callback:
            access_code = self.two_factor_auth_callback(self.auth_username)
        else:
            access_code = ask_for_2fa_code(self.auth_username)
        self.logger.debug("REST Authenticating 2FA phase 2")
        return self.query('authenticate',
                          method='POST',
                          data={'username': self.auth_username,
                                'password': access_code,
                                "two_factor_auth_phase": 1,
                                "temp_token": temp_token},
                          do_not_log_reponse=True)['access_token']

    def set_token(self, access_token) -> None:
        """Add the Centra API JWT authentication token to the session object headers"""
        self.logger.debug("Setting Centra API access token")
        self.access_token = access_token
        self._http.headers.update({"Authorization": f"bearer {access_token}"})

    def paginate(self,
                 endpoint: str,
                 method: str,
                 objects_per_page: int = None,
                 params: Dict[str, str] = None,
                 yield_objects: bool = True) -> Generator:
        """
        Send a request to Centra in pages, and yield the pages
        :param endpoint: Centra Rest API endpoint to query
        :param method: HTTP request method as uppercase string (e.g. GET, POST, PUT)
        :param params: HTTP request query parameters
        :param objects_per_page: Limit the number of objects per page. If omitted, Centra will use the default page
        size according to the requested endpoint
        :param yield_objects: If True, only the response objects (and not the entire response) will be yielded
        """
        if not params:
            params = {}
        if objects_per_page:
            params["limit"] = objects_per_page

        first_res = self.query(endpoint, method, params=params)
        if yield_objects:
            yield first_res["objects"]
        else:
            yield first_res

        total_count = first_res["total_count"]
        per_page = first_res["results_in_page"]
        num_pages = math.ceil(total_count / per_page)

        offset = first_res["to"]

        for _ in range(2, num_pages + 1):
            next_res = self.query(endpoint, method, params={"offset": offset, "limit": per_page, **params})
            offset = next_res["to"]
            if yield_objects:
                yield next_res["objects"]
            else:
                yield next_res

    def set_base_api_path(self, base_api_path: str) -> None:
        """
        Set a new base API path, and re create the base url for all future API requests
        :param base_api_path: The new base api path to use
        """
        self.base_api_path = base_api_path
        self.http_base_url = f'https://{self.management_address}:{self.management_api_port}/{self.base_api_path}'

    def logout(self) -> None:
        """ Logout from Centra API """
        logger.debug("Logging out from Centra API")
        self.query('logout', method='POST', return_json=False)

    def close(self) -> None:
        """Logout from Centra API, suppressing errors"""
        try:
            self.logout()
        except CentraAPIBaseError as e:
            logger.debug(f"Could not logout properly from Centra API. {e}")
