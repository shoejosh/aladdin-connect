import base64
import json
import logging
import requests


class SessionManager:
    HEADER_CONTENT_TYPE_URLENCODED = 'application/x-www-form-urlencoded'
    HEADER_USER_AGENT = "okhttp/3.12.1"
    HEADER_BUNDLE_NAME = "com.geniecompany.AladdinConnect"
    HEADER_BUILD_VERSION = "131"
    HEADER_APP_VERSION = "5.25"

    API_BASE_URL = "https://pxdqkls7aj.execute-api.us-east-1.amazonaws.com/Android"
    RPC_URL = API_BASE_URL

    LOGIN_ENDPOINT = "/oauth/token"
    X_API_KEY = "fkowarQ0dX9Gj1cbB9Xkx1yXZkd6bzVn5x24sECW"

    _LOGGER = logging.getLogger(__name__)

    def __init__(self, email, password):
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': self.HEADER_CONTENT_TYPE_URLENCODED,
                                      'AppVersion': self.HEADER_APP_VERSION,
                                      'BundleName': self.HEADER_BUNDLE_NAME,
                                      'User-Agent': self.HEADER_USER_AGENT,
                                      'BuildVersion': self.HEADER_BUILD_VERSION,
                                      'X-Api-Key': self.X_API_KEY})
        self._auth_token = None
        self._user_email = email
        self._password = password
        self._logged_in = False

    def login(self):
        self._auth_token = None
        self._logged_in = False

        try:
            password_base64 = base64.b64encode(self._password.encode('utf-8')).decode('utf-8')
            response = self.call_api(self.LOGIN_ENDPOINT, method="post",
                                     payload={"grant_type": "password",
                                              "client_id": "1000",
                                              "brand": "ALADDIN",
                                              "username": self._user_email,
                                              "password": password_base64,
                                              "platform": "platform",
                                              "model": "Google Pixel 6",
                                              "app_version": "5.25",
                                              "build_number": "2038",
                                              "os_version": "12.0.0"})
            if response and "access_token" in response:
                self._logged_in = True
                self._auth_token = response["access_token"]
                self._session.headers.update({'Authorization': f'Bearer {self._auth_token}'})
                return True
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to login %s", ex)

        return False

    def call_api(self, api, payload=None, method='get', response_type='json'):
        self._session.headers.update({'Content-Type': 'application/x-www-form-urlencoded'})
        return self._rest_call(
            self.API_BASE_URL + api,
            payload,
            method,
            request_type='text',
            response_type=response_type
        )

    def call_rpc(self, api, payload=None, method='post', response_type='json'):
        self._session.headers.update({'Content-Type': 'application/json'})
        return self._rest_call(
            self.RPC_URL + api,
            payload,
            method,
            request_type='json',
            response_type=response_type
        )

    def _rest_call(
        self,
        uri,
        payload=None,
        method='get',
        request_type='text',
        response_type='json'
    ):
        """Generic method for calling REST APIs."""
        # Sanity check parameters first...
        if method not in ('get', 'post', 'put', 'delete'):
            msg = "Tried call_api with bad method: {0}"
            raise ValueError(msg.format(method))

        try:
            if request_type == 'json':
                response = getattr(self._session, method)(uri, json=payload)
            else:
                response = getattr(self._session, method)(uri, data=payload)
        except requests.exceptions.HTTPError as ex:
            self._LOGGER.error("Aladdin Connect - API Error %s", ex)
            return None

        # Unauthorized
        if response.status_code in (401, 403):
            # Maybe we got logged out? Let's try logging in if we've been logged in previously.
            if self._logged_in and self.login():
                # Retry the request...
                response = getattr(self._session, method)(uri, data=payload)

        if response.status_code not in (200, 204):
            msg = f"Aladdin API call ({uri}) failed: {response.status_code}, {response.text}"
            raise ValueError(msg)

        if response.text is not None and len(response.text) > 0:
            if response_type == 'text':
                return response.text
            return json.loads(response.text)
        return None
