import base64
import json
import logging
import requests


class SessionManager:
    HEADER_USER_AGENT = "Aladdin Connect Android v2.10.1'"
    HEADER_BUNDLE_NAME = "com.geniecompany.AladdinConnect"
    HEADER_BUILD_VERSION = "131"
    HEADER_APP_VERSION = "2.10.1"

    API_BASE_URL = "https://genie.exosite.com/api/portals/v1"
    RPC_URL = "https://genie.m2.exosite.com/onep:v1/rpc/process"

    LOGIN_ENDPOINT = "/users/_this/token"

    _LOGGER = logging.getLogger(__name__)

    def __init__(self, email, password):
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': 'application/json',
                                      'AppVersion': self.HEADER_APP_VERSION,
                                      'BundleName': self.HEADER_BUNDLE_NAME,
                                      'User-Agent': self.HEADER_USER_AGENT,
                                      'BuildVersion': self.HEADER_BUILD_VERSION})
        self._login_token = base64.b64encode("{}:{}".format(email, password).encode('utf-8')).decode('utf-8')
        self._auth_token = None
        self._user_email = email
        self._logged_in = False

    def login(self):
        self._auth_token = None
        self._logged_in = False

        self._session.headers.update({'Authorization': 'Basic {}'.format(self._login_token)})

        try:
            response = self.call_api(self.LOGIN_ENDPOINT, response_type='text')
            if response:
                self._logged_in = True
                self._auth_token = response
                self._session.headers.update({'Authorization': 'Token: {}'.format(self._auth_token)})
                return True
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to login %s", ex)

        return False

    def call_api(self, api, payload=None, method='get', response_type='json'):
        return self._rest_call(self.API_BASE_URL + api, payload, method, response_type)

    def call_rpc(self, payload=None, method='post', response_type='json'):
        return self._rest_call(self.RPC_URL, payload, method, response_type)

    def _rest_call(self, uri, payload=None, method='get', response_type='json'):
        """Generic method for calling REST APIs."""
        # Sanity check parameters first...
        if (method != 'get' and method != 'post' and
                method != 'put' and method != 'delete'):
            msg = "Tried call_api with bad method: {0}"
            raise ValueError(msg.format(method))

        # Payload is always JSON
        if payload is not None:
            payload_json = json.dumps(payload)
        else:
            payload_json = ''

        try:
            response = getattr(self._session, method)(uri, data=payload_json)
        except requests.exceptions.HTTPError as ex:
            self._LOGGER.error("Aladding Connect - API Error %s", ex)
            return None

        # Unauthorized
        if response.status_code == 401 or response.status_code == 403:
            # Maybe we got logged out? Let's try logging in if we've been logged in previously.
            if self._logged_in and self.login():
                # Retry the request...
                response = getattr(self._session, method)(uri, data=payload_json)

        if response.status_code != 200 and response.status_code != 204:
            msg = "Aladdin API call ({0}) failed: {1}, {2}".format(
                uri, response.status_code, response.text)
            raise ValueError(msg)

        if response.text is not None and len(response.text) > 0:
            if response_type == 'text':
                return response.text
            return json.loads(response.text)
        else:
            return None
