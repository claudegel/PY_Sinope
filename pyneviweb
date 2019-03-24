class NeviwebClient(object):

    def __init__(self, username, password, network, timeout=REQUESTS_TIMEOUT):
        """Initialize the client object."""
        self._username = username
        self._password = password
        self._network_name = network
        self._gateway_id = None
        self.gateway_data = {}
        self._headers = None
        self._cookies = None
        self._timeout = timeout
        self.user = None

        self.__post_login_page()
        self.__get_network()
        self.__get_gateway_data()

    def update(self):
        self.__get_gateway_data()

    def __post_login_page(self):
        """Login to Neviweb."""
        data = {"email": self._username, "password": self._password, 
            "stayConnected": 1}
        try:
            raw_res = requests.post(LOGIN_URL, data=data, 
                cookies=self._cookies, allow_redirects=False, 
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot submit login form")
        if raw_res.status_code != 200:
            raise PyNeviwebError("Cannot log in")

        # Update session
        self._cookies = raw_res.cookies
        data = raw_res.json()
        self.user = data["user"]
        self._headers = {"Session-Id": data["session"]}
        _LOGGER.debug("Successfully logged in: %s", self.user)
        return True

    def __get_network(self):
        """Get gateway id associated to the desired network."""
        # Http request
        try:
            raw_res = requests.get(GATEWAY_URL, headers=self._headers, 
                cookies=self._cookies, timeout=self._timeout)
            networks = raw_res.json()

            if self._network_name == None: # Use 1st network found
                self._gateway_id = networks[0]["id"]
                self._network_name = networks[0]["name"]
            else:
                for network in networks:
                    if network["name"] == self._network_name:
                        self._gateway_id = network["id"]
                        break
            _LOGGER.debug("Selecting %s network among: %s",
                self._network_name, networks)
        except OSError:
            raise PyNeviwebError("Cannot get network")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        self.gateway_data = raw_res.json()

    def __get_gateway_data(self):
        """Get gateway data."""
        # Http request
        try:
            raw_res = requests.get(GATEWAY_DEVICE_URL + str(self._gateway_id),
                headers=self._headers, cookies=self._cookies, 
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot get gateway data")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
#        _LOGGER.debug("Neviweb gateway data: %s", raw_res.json())
        self.gateway_data = raw_res.json()

    def get_device_data(self, device_id):
        """Get device data."""
        # Prepare return
        data = {}
        # Http request
        try:
            raw_res = requests.get(DEVICE_DATA_URL + str(device_id) +
                "/data?force=1", headers=self._headers, cookies=self._cookies,
                timeout=self._timeout)
        except requests.exceptions.ReadTimeout:
            return {"errorCode": "ReadTimeout"}
        except Exception as e:
            raise PyNeviwebError("Cannot get page data_device", e)
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
 #       _LOGGER.debug("device data: %s", data)
        return data

    def get_device_info(self, device_id):
        """Get gateway information for this device."""
        self.__get_gateway_data()
        for device_info in self.gateway_data:
            if device_info["id"] == device_id:
                return device_info
        return None

    def get_device_properties(self, device_id):
        """Get device properties."""
        # Prepare return
        data = {}
        # Http request
        try:
            raw_res = requests.get(DEVICE_DATA_URL + str(device_id) +
                "/properties?force=1", headers=self._headers,
                cookies=self._cookies, timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot get properties page")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
#        _LOGGER.warning("Sinope properties = %s", data)
        return data

    def ping_device(self, device_id):
        """Ping a device."""
        # Prepare return
        data = {}
        # Http request
        try:
            raw_res = requests.get(DEVICE_DATA_URL + str(device_id) +
                "/ping?force=1", headers=self._headers, cookies=self._cookies,
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot ping device")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        return data

    def get_device_daily_stats(self, device_id):
        """Get device power consumption (in watts) for the last 30 days."""
        # Prepare return
        data = {}
        stats = []
        # Http request
        try:
            raw_res = requests.get(DEVICE_DATA_URL + str(device_id) +
                    "/statistics/byDay?force=1", headers=self._headers,
                    cookies=self._cookies, timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot get device daily stats")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        for day in data:
            stats.append(day["value"])
        return stats

    def get_device_hourly_stats(self, device_id):
        """Get device power consumption (in watts) for the last 24 hours."""
        # Prepare return
        data = {}
        stats = []
        # Http request
        try:
            raw_res = requests.get(DEVICE_DATA_URL + str(device_id) +
                "/statistics/byHour?force=1", headers=self._headers,
                cookies=self._cookies, timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot get device daily stats")
        # Update cookies
        self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        for hour in data:
            stats.append(hour["value"])
        return stats

    def set_brightness(self, device_id, brightness):
        """Set device intensity."""
        data = {"intensity": brightness}
        try:
            requests.put(DEVICE_DATA_URL + str(device_id) + "/intensity",
                data=data, headers=self._headers, cookies=self._cookies,
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot set device brightness")

    def set_mode(self, device_id, mode):
        """Set device operation mode."""
        data = {"mode": mode}
        try:
            requests.put(DEVICE_DATA_URL + str(device_id) + "/mode",
                data=data, headers=self._headers, cookies=self._cookies,
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot set device operation mode")

    def set_temperature(self, device_id, temperature):
        """Set device temperature."""
        data = {"temperature": temperature}
        try:
            requests.put(DEVICE_DATA_URL + str(device_id) + "/setpoint",
                data=data, headers=self._headers, cookies=self._cookies,
                timeout=self._timeout)
        except OSError:
            raise PyNeviwebError("Cannot set device temperature")
