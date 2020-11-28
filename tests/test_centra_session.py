import requests_mock

from unittest import TestCase
from unittest.mock import patch

from centra_py_client.centra_session import CentraSession
from centra_py_client.exceptions.session import CentraAuthError, NoPermissionToAccessResource, CentraAPIError, \
    CentraAPIRequestTimeout, BadAPIRequest, RedirectionRequiredError


class TestCentraSession(TestCase):
    @staticmethod
    def get_centra_session(**kwargs) -> CentraSession:
        """
        Get a Centra session with fake management address, username and password. Any keyword argument will be
        passed to the CentraSession constructor.
        """
        return CentraSession(management_address="centra.foo.com", auth_username="username",
                             auth_password="password", **kwargs)

    @patch("centra_py_client.centra_session.CentraSession._query")
    def test_login_is_not_performed_if_login_is_false(self, mock_centra_query):
        """
        Validate no request is sent to Centra for authentication when initiating a new CentraSession
        if login=False
        """
        session = self.get_centra_session(login=False)

        mock_centra_query.assert_not_called()

    @patch("centra_py_client.centra_session.CentraSession._perform_two_factor_authentication")
    @patch("centra_py_client.centra_session.CentraSession.query")
    def test_2fa_performed_if_required_and_enabled(self, initial_login_request, two_factor_auth):
        """Test 2fa is performed when required and enabled"""
        initial_login_request.return_value = {"2fa_required": True, "2fa_temp_token": "foo"}

        session = self.get_centra_session(allow_two_factor_auth=True)

        two_factor_auth.assert_called()

    @patch("centra_py_client.centra_session.CentraSession._perform_two_factor_authentication")
    @patch("centra_py_client.centra_session.CentraSession.query")
    def test_2fa_not_performed_if_not_enabled(self, initial_login_request, two_factor_auth):
        """Test 2fa is not performed when required but not enabled"""
        initial_login_request.return_value = {"2fa_required": True, "2fa_temp_token": "foo"}

        with self.assertRaises(CentraAuthError):
            self.get_centra_session(allow_two_factor_auth=False)

        two_factor_auth.assert_not_called()

    @patch("centra_py_client.centra_session.ask_for_2fa_code")
    @patch("centra_py_client.centra_session.CentraSession.query")
    def test_user_is_prompted_for_2fa_code(self, centra_queries, ask_for_2fa_code):
        """Test the user is prompted for 2fa code if 2fa is required but 2fa callback was not provided"""
        centra_queries.side_effect = [
            {"2fa_required": True, "2fa_temp_token": "foo"},
            {"access_token": "bar"}
        ]

        session = self.get_centra_session(allow_two_factor_auth=True)

        ask_for_2fa_code.assert_called_once()

    @patch("centra_py_client.centra_session.ask_for_2fa_code")
    @patch("centra_py_client.centra_session.CentraSession.query")
    def test_user_is_not_prompted_for_2fa_code_if_callback_was_provided(self, centra_queries, ask_for_2fa_code):
        """Validate the user is not prompted for 2fa code if 2fa is required and 2fa callback was provided"""
        centra_queries.side_effect = [
            {"2fa_required": True, "2fa_temp_token": "foo"},
            {"access_token": "bar"}
        ]

        session = self.get_centra_session(allow_two_factor_auth=True,
                                          two_factor_auth_callback=lambda x: x)

        ask_for_2fa_code.assert_not_called()

    @patch("centra_py_client.centra_session.CentraSession.query")
    def test_2fa_callback_function_is_running_if_provided_and_required(self, centra_queries):
        """Validate 2fa callback function is running if provided and 2fa is required"""
        centra_queries.side_effect = [
            {"2fa_required": True, "2fa_temp_token": "foo"},
            {"access_token": "bar"}
        ]

        def two_fa_callback(username):
            return "passcode"

        session = self.get_centra_session(allow_two_factor_auth=True,
                                          two_factor_auth_callback=two_fa_callback)

        self.assertTrue(centra_queries.call_args[1]["data"]["password"] == "passcode")

    @patch("requests.Session.post")
    def test_re_authentication_is_not_performed_if_last_authentication_request_was_not_successful(self, post_request):
        """
        Validate authentication is not performed twice if the first attempt failed, and that CentraAuthError is raised.
        This should make sure the decorator rest_auto_reconnect does not cause an infinite loop of login attempts.
        """
        post_request.side_effect = CentraAuthError()

        with patch("centra_py_client.centra_session.CentraSession.login",
                   side_effect=CentraSession.login,
                   autospec=True) as login:
            with self.assertRaises(CentraAuthError):
                session = self.get_centra_session()

            login.assert_called_once()

    @requests_mock.Mocker()
    def test_re_authentication_is_called_if_last_authentication_request_was_successful(self, http_mocker):
        """
        Validate authentication is performed again if CentraAuthError is raised after the last login attempt was
        successful, and that and CentraAuthError is not raised further in case the second authentication is successful.
        """
        centra_session = self.get_centra_session(login=False)
        centra_session.last_rest_auth_attempt_was_successful = True
        http_mocker.get(centra_session.get_api_request_uri("foo"),
                        status_code=401,
                        headers={"Content-Type": "application/json"},
                        content=b'{"error": "foo", "description": "bar"}')
        with patch("centra_py_client.centra_session.CentraSession.login") as login:

            try:
                centra_session._query("foo")
            except CentraAuthError:
                pass

            login.assert_called_once()

    @requests_mock.Mocker()
    def test_re_authentication_is_not_called_if_rest_auto_reconnect_is_false(self, http_mocker):
        """Validate authentication is not performed again if rest_auto_reconnect is False"""
        centra_session = self.get_centra_session(login=False,
                                                 auto_reconnect=False)
        centra_session.last_rest_auth_attempt_was_successful = True
        http_mocker.get(centra_session.get_api_request_uri("foo"),
                        status_code=401,
                        headers={"Content-Type": "application/json"},
                        content=b'{"error": "foo", "description": "bar"}')
        with patch("centra_py_client.centra_session.CentraSession.login") as login:

            try:
                centra_session._query("foo")
            except CentraAuthError:
                pass

            login.assert_not_called()

    @requests_mock.Mocker()
    def test_centra_auth_error_is_raised_if_response_status_code_is_401(self, http_mocker):
        """Validate CentraAuthError is raised if the response from Centra is HTTP code 401"""

        session = self.get_centra_session(login=False)
        http_mocker.post(session.get_api_request_uri("authenticate"),
                         status_code=401,
                         headers={"Content-Type": "application/json"},
                         content=b'{"error": "foo", "description": "bar"}')

        with self.assertRaises(CentraAuthError):
            session.login()

    @requests_mock.Mocker()
    def test_centra_no_permission_error_is_raised_if_response_code_is_403(self, http_mocker):
        """Validate NoPermissionToAccessResource is raised if the response from Centra is HTTP code 403"""

        session = self.get_centra_session(login=False)
        http_mocker.get(session.get_api_request_uri("foo"),
                        status_code=403,
                        headers={"Content-Type": "application/json"},
                        content=b'{"error": "foo", "description": "bar"}')

        with self.assertRaises(NoPermissionToAccessResource):
            session._query("foo")

    @requests_mock.Mocker()
    def test_centra_api_error_is_raised_if_response_is_error_with_json_content(self, http_mocker):
        """
        Validate CentraAPIError is raised for every error response from Centra that contains json and is not a
        permission or authentication error
        """

        session = self.get_centra_session(login=False)
        for error_code in [code for code in range(400, 600) if code not in (401, 403)]:
            http_mocker.get(session.get_api_request_uri("foo"),
                            status_code=error_code,
                            headers={"Content-Type": "application/json"},
                            content=b'{"error": "foo", "description": "bar"}')

            with self.assertRaises(CentraAPIError):
                session._query("foo")

    @requests_mock.Mocker()
    def test_centra_api_timeout_error_is_raised_if_response_code_is_504(self, http_mocker):
        """Validate CentraAPIRequestTimeout is raised if the response from Centra is HTTP code 504"""

        session = self.get_centra_session(login=False)
        http_mocker.get(session.get_api_request_uri("foo"),
                        status_code=504)

        with self.assertRaises(CentraAPIRequestTimeout):
            session._query("foo")

    @requests_mock.Mocker()
    def test_bad_api_request_error_is_raised_if_response_code_is_404(self, http_mocker):
        """Validate BadAPIRequest is raised if the response from Centra is HTTP code 404"""

        session = self.get_centra_session(login=False)
        http_mocker.get(session.get_api_request_uri("foo"),
                        status_code=404)

        with self.assertRaises(BadAPIRequest):
            session._query("foo")

    @requests_mock.Mocker()
    def test_location_redirection_is_done_following_response_code_406(self, http_mocker):
        """Validate Location redirection after HTTP response 406 is successful"""

        session = self.get_centra_session(login=False)
        redirect_from = "foo"
        redirect_to = "bar"
        http_mocker.get(session.get_api_request_uri(redirect_from),
                        status_code=406,
                        headers={"Location": redirect_to})
        http_mocker.get(session.get_api_request_uri(redirect_to),
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        content=b'{"success": "true"}')

        response = session.query(redirect_from)

        self.assertTrue(response["success"] == "true")

    @requests_mock.Mocker()
    def test_location_redirection_is_not_done_if_not_enabled(self, http_mocker):
        """Validate Location redirection is not performed after HTTP response 406 if self.follow_redirects is False"""

        session = self.get_centra_session(follow_redirects=False,
                                          login=False)
        redirect_from = "foo"
        redirect_to = "bar"
        http_mocker.get(session.get_api_request_uri(redirect_from),
                        status_code=406,
                        headers={"Location": redirect_to})

        with self.assertRaises(RedirectionRequiredError):
            try:
                response = session.query(redirect_from)
            except requests_mock.exceptions.NoMockAddress:
                self.fail("NoMockAddress was unexpectedly raised, which means there was an unexpected http request")

    @requests_mock.Mocker()
    def test_paginate(self, http_mocker):
        """ Test paginating responses from Centra """
        session = self.get_centra_session(login=False)
        endpoint = "foo"
        http_mocker.get(session.get_api_request_uri(endpoint),
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        content=b'''
                        {
                            "total_count": 5,
                            "results_in_page": 1,
                            "to": 1,
                            "objects": [{"foo": "bar"}]
                        }
                        ''')
        pages_count = 0

        for _ in session.paginate(endpoint, 'GET', objects_per_page=1):
            pages_count += 1

        self.assertTrue(pages_count == 5)
