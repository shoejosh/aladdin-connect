import logging
from typing import Dict, Any

from aladdin_connect.session_manager import SessionManager


class AladdinConnectClient:
    USER_DETAILS_ENDPOINT = "/users/_this"
    GET_USER_PORTALS_ENDPOINT = "/users/{user_id}/portals"
    GET_PORTAL_DETAILS_ENDPOINT = "/portals/{portal_id}"

    DOOR_STATUS_OPEN = 'open'
    DOOR_STATUS_CLOSED = 'closed'
    DOOR_STATUS_OPENING = 'opening'
    DOOR_STATUS_CLOSING = 'closing'
    DOOR_STATUS_UNKNOWN = 'unknown'

    DOOR_STATUS = {
        0: DOOR_STATUS_UNKNOWN,  # Unknown
        1: DOOR_STATUS_OPEN,  # open
        2: DOOR_STATUS_OPENING,  # opening
        3: DOOR_STATUS_UNKNOWN,  # Timeout Opening
        4: DOOR_STATUS_CLOSED,  # closed
        5: DOOR_STATUS_CLOSING,  # closing
        6: DOOR_STATUS_UNKNOWN,  # Timeout Closing
        7: DOOR_STATUS_UNKNOWN  # Not Configured
    }

    REQUEST_DOOR_STATUS = {
        DOOR_STATUS_CLOSED: '0',
        DOOR_STATUS_OPEN: '1'
    }

    STATUS_CONNECTED = 'Connected'
    STATUS_NOT_CONFIGURED = 'NotConfigured'

    DOOR_LINK_STATUS = {
        0: 'Unknown',
        1: STATUS_NOT_CONFIGURED,
        2: 'Paired',
        3: STATUS_CONNECTED
    }

    CONTROLLER_STATUS = {
        0: 'Offline',
        1: STATUS_CONNECTED
    }

    _LOGGER = logging.getLogger(__name__)

    def __init__(self, email, password):
        self._session = SessionManager(email, password)
        self._user_email = email
        self._device_portal = {}

    def login(self):
        return self._session.login()

    def get_doors(self):
        devices = self._get_devices()

        doors = []

        if devices:
            for device in devices:
                doors += device['doors']

        return doors

    def _get_devices(self):
        """Get list of devices, i.e., Aladdin Door Controllers"""

        # get the user id
        try:
            user = self._session.call_api(self.USER_DETAILS_ENDPOINT, method='get')
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to retrieve user details %s", ex)
            return

        # get portals associated with user
        try:
            portals = self._session.call_api(self.GET_USER_PORTALS_ENDPOINT.format(user_id=user['id']), method='get')
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to retrieve user portals %s", ex)
            return

        # for each portal get the list of devices
        devices = []
        self._device_portal.clear()
        for portal in portals:
            # only include portals that belong to user, i.e. not a portal that has been shared with user
            if portal['UserEmail'] != self._user_email:
                continue
            try:
                portal_details = self._session.call_api(self.GET_PORTAL_DETAILS_ENDPOINT.format(portal_id=portal["PortalID"]),
                                                method='get')
            except ValueError as ex:
                self._LOGGER.error("Aladdin Connect - Unable to retrieve portal details %s", ex)
                return

            portal_id = portal_details["info"]["key"]

            # we will need the portal id and device id to issue commands to doors connected to the device
            for device_id in portal_details['devices']:
                # save portal id in dict by device id, no need to expose this to users
                self._device_portal[device_id] = portal_id
                devices.append({
                    'device_id': device_id,
                    'doors': self._get_doors_for_device(device_id)
                })

        return devices

    def _get_doors_for_device(self, device_id):
        payload = self._get_payload_auth_for_device(device_id)
        payload['calls'] = [
            self._get_read_rpc_call('dps1.link_status', 1),
            self._get_read_rpc_call('dps1.name', 2),
            self._get_read_rpc_call('dps1.door_status', 3),

            self._get_read_rpc_call('dps2.link_status', 4),
            self._get_read_rpc_call('dps2.name', 5),
            self._get_read_rpc_call('dps2.door_status', 6),

            self._get_read_rpc_call('dps2.link_status', 7),
            self._get_read_rpc_call('dps2.name', 8),
            self._get_read_rpc_call('dps2.door_status', 9)
        ]

        try:
            response = self._session.call_rpc(payload)
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to get doors for device %s", ex)
            return None

        doors = []
        for x in range(0, 3):
            door_response = response[x*3:x*3+3]
            link_status_id = door_response[0]['result'][0][1]
            if self.DOOR_LINK_STATUS[link_status_id] is not self.STATUS_NOT_CONFIGURED:
                name = door_response[1]['result'][0][1]
                door_status_id = door_response[2]['result'][0][1]
                doors.append({
                    'device_id': device_id,
                    'door_number': x + 1,
                    'name': name,
                    'status': self.DOOR_STATUS[door_status_id],
                    'link_status': self.DOOR_LINK_STATUS[link_status_id]
                })
        return doors

    def close_door(self, device_id, door_number):
        self._set_door_status(device_id, door_number, self.REQUEST_DOOR_STATUS[self.DOOR_STATUS_CLOSED])

    def open_door(self, device_id, door_number):
        self._set_door_status(device_id, door_number, self.REQUEST_DOOR_STATUS[self.DOOR_STATUS_OPEN])

    def _set_door_status(self, device_id, door_number, state):
        """Set door state"""
        payload = self._get_payload_auth_for_device(device_id)
        payload['calls'] = [
            self._get_write_rpc_call(f'dps{door_number}.desired_status', 0, state),
            self._get_write_rpc_call(f'dps{door_number}.desired_status_user', 1, self._user_email)
        ]

        try:
            self._session.call_rpc(payload)
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to set door status %s", ex)
            return False

        return True

    def get_door_status(self, device_id, door_number):
        payload = self._get_payload_auth_for_device(device_id)
        payload['calls'] = [
            self._get_read_rpc_call(f'dps{door_number}.door_status', 1),
        ]

        try:
            response = self._session.call_rpc(payload)
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to get doors status %s", ex)
            return None

        status = response[0]['result'][0][1]
        return self.DOOR_STATUS[status]

    def _get_payload_auth_for_device(self, device_id) -> Dict[str, Any]:
        portal_id = self._device_portal[device_id]
        return {
            'auth': {
                'cik': portal_id,
                'client_id': device_id
            }
        }

    @staticmethod
    def _get_read_rpc_call(alias, index):
        return {
            'arguments': [
                {
                    'alias': alias
                },
                {}
            ],
            'id': index,
            'procedure': 'read'
        }

    @staticmethod
    def _get_write_rpc_call(alias, index, val):
        return {
            'arguments': [
                {
                    'alias': alias
                },
                val
            ],
            'id': index,
            'procedure': 'write'
        }
