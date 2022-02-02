import logging

from aladdin_connect.session_manager import SessionManager


class AladdinConnectClient:
    CONFIGURATION_ENDPOINT = "/configuration"

    DOOR_STATUS_OPEN = 'open'
    DOOR_STATUS_CLOSED = 'closed'
    DOOR_STATUS_OPENING = 'opening'
    DOOR_STATUS_CLOSING = 'closing'
    DOOR_STATUS_UNKNOWN = 'unknown'

    DOOR_COMMAND_CLOSE = "CloseDoor"
    DOOR_COMMAND_OPEN = "OpenDoor"

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

    REQUEST_DOOR_STATUS_COMMAND = {
        DOOR_STATUS_CLOSED: DOOR_COMMAND_CLOSE,
        DOOR_STATUS_OPEN: DOOR_COMMAND_OPEN
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

        try:
            response = self._session.call_api(self.CONFIGURATION_ENDPOINT, method='get')
            devices = []
            for device in response["devices"]:
                doors = []
                for door in device["doors"]:
                    doors.append({
                        'device_id': device["id"],
                        'door_number': door["door_index"],
                        'name': door["name"],
                        'status': self.DOOR_STATUS[door["status"]],
                        'link_status': self.DOOR_LINK_STATUS[door["link_status"]]
                    })
                devices.append({
                    'device_id': device["id"],
                    'doors': doors
                })
            return devices
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to retrieve configuration %s", ex)
            return None

    def close_door(self, device_id, door_number):
        self._set_door_status(device_id, door_number, self.DOOR_STATUS_CLOSED)

    def open_door(self, device_id, door_number):
        self._set_door_status(device_id, door_number, self.DOOR_STATUS_OPEN)

    def _set_door_status(self, device_id, door_number, requested_door_status):
        """Set door state"""
        payload = {"command_key": self.REQUEST_DOOR_STATUS_COMMAND[requested_door_status]}

        try:
            self._session.call_rpc(f"/devices/{device_id}/door/{door_number}/command", payload)
        except ValueError as ex:
            # Ignore "Door is already open/closed" errors to maintain backwards compatibility
            error = str(ex.args[0])
            should_ignore = error.endswith(
                f'{{"code":400,"error":"Door is already {requested_door_status}"}}')
            if not should_ignore:
                self._LOGGER.error("Aladdin Connect - Unable to set door status %s", ex)
                return False

        return True

    def get_door_status(self, device_id, door_number):
        try:
            doors = self.get_doors()
            for door in doors:
                if door["device_id"] == device_id and door["door_number"] == door_number:
                    return door["status"]
        except ValueError as ex:
            self._LOGGER.error("Aladdin Connect - Unable to get door status %s", ex)
        return self.DOOR_STATUS_UNKNOWN
