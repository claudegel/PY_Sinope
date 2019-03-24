import struct
import binascii
import socket
import sys
import crc8
import requests
import json
from datetime import datetime
import pytz
from astral import Astral

PORT = 4550
#city_name = 'Montreal'
#tz = pytz.timezone('America/Toronto')
all_unit = "FFFFFFFF"
#sequential number to identify the current request. Could be any unique number that is different at each request
# could we use timestamp value ?
seq_num = 12345678 
seq = 0

# command type
data_read_command = "4002"
data_report_command = "4202"
data_write_command = "4402"

#thermostat data read
data_heat_level = "20020000" #0 to 100%
data_mode = "11020000" # off, manual, auto, bypass, away...
data_temperature = "03020000" #room temperature
data_setpoint = "08020000" #thermostat set point
data_away = "00070000"  #set device mode to away, 0=home, 2=away

#thermostat info read
data_display_format = "00090000" # 0 = celcius, 1 = fahrenheit
data_time_format = "01090000" # 0 = 24h, 1 = 12h
data_lock = "02090000" # 0 = unlock, 1 = lock
data_load = "000D0000" # 0-65519 watt, 1=1 watt, (2 bytes)
data_display2 = "30090000" # 0 = default setpoint, 1 = outdoor temp.
data_min_temp = "0A020000" # Minimum room setpoint, 5-30oC (2 bytes)
data_max_temp = "0B020000" # Maximum room setpoint, 5-30oC (2 bytes)
data_away_temp = "0C020000" # away room setpoint, 5-30oC (2 bytes)

# thermostat data report
data_outdoor_temperature = "04020000" #to show on thermostat, must be sent at least every hour
data_time = "00060000" #must be sent at least once a day or before write request for auto mode
data_date = "01060000" 
data_sunrise = "20060000" #must be sent onece a day
data_sunset = "21060000" #must be sent onece a day

# thermostat data write
data_early_start = "60080000"  #0=disabled, 1=enabled

# light and dimmer
data_light_intensity = "00100000"  # 0 to 100, off to on, 101 = last level
data_light_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_light_timer = "000F0000"   # time in minutes the light will stay on 0--255
data_light_event = "010F0000"  #0= no event sent, 1=timer active, 2= event sent for turn_on or turn_off

# Power control
data_power_intensity = "00100000"  # 0 to 100, off to on
data_power_mode = "09100000"  # 1=manual, 2=auto, 3=random or away, 130= bypass auto
data_power_connected = "000D0000" # actual load connected to the device
data_power_load = "020D0000" # load used by the device
data_power_event = "010F0000"  #0= no event sent, 1=timer active, 2= event sent for turn_on or turn_off
data_power_timer = "000F0000" # time in minutes the power will stay on 0--255

class SinopeClient(object):

    def __init__(self, api_key, api_id, server, city_name, tz, latitude, longitude, timeout=REQUESTS_TIMEOUT):
        """Initialize the client object."""
        self._api_key = api_key
        self._api_id = api_id
        self._network_name = server
        self._city_name = city_name
        self._tz = tz
        self._latitude = latitude
        self._longitude = longitude
        self.device_data = {}

    def crc_count(bufer):
        hash = crc8.crc8()
        hash.update(bufer)
        return hash.hexdigest()

    def crc_check(bufer):
        hash = crc8.crc8()
        hash.update(bufer)
        if(hash.hexdigest() == "00"):
          return "00"
        return None

    def get_dst(): # daylight saving time is on or not
        localtime = datetime.now(self._tz)
        if localtime.dst():
            return 128
        return 0

    def set_date():
        now = datetime.now(self._tz)
        day = int(now.strftime("%w"))-1
        if day == -1:
            day = 6
        w = bytearray(struct.pack('<i', day)[:1]).hex() #day of week, 0=monday converted to bytes
        d = bytearray(struct.pack('<i', int(now.strftime("%d")))[:1]).hex() #day of month converted to bytes
        m = bytearray(struct.pack('<i', int(now.strftime("%m")))[:1]).hex() #month converted to bytes
        y = bytearray(struct.pack('<i', int(now.strftime("%y")))[:1]).hex() #year converted to bytes
        date = '04'+w+d+m+y #xxwwddmmyy,  xx = lenght of data date = 04
        return date

    def set_time():
        now = datetime.now(self._tz)
        s = bytearray(struct.pack('<i', int(now.strftime("%S")))[:1]).hex() #second converted to bytes
        m = bytearray(struct.pack('<i', int(now.strftime("%M")))[:1]).hex() #minutes converted to bytes
        h = bytearray(struct.pack('<i', int(now.strftime("%H"))+get_dst())[:1]).hex() #hours converted to bytes
        time = '03'+s+m+h #xxssmmhh  24hr, 16:09:00 pm, xx = lenght of data time = 03
        return time
  
    def set_sun_time(period): # period = sunrise or sunset
        a = Astral()
        city = a[self._city_name]
        sun = city.sun(date=datetime.now(self._tz), local=True)
        if period == "sunrise":
            now = sun['sunrise']
        else:
            now = sun['sunset']
        s = bytearray(struct.pack('<i', int(now.strftime("%S")))[:1]).hex() #second converted to bytes
        m = bytearray(struct.pack('<i', int(now.strftime("%M")))[:1]).hex() #minutes converted to bytes
        h = bytearray(struct.pack('<i', int(now.strftime("%H"))+get_dst())[:1]).hex() #hours converted to bytes
        time = '03'+s+m+h #xxssmmhh  24hr, 16:09:00 pm, xx = lenght of data time = 03
        return time
  
    def get_heat_level(data):
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[46:]
        tc2 = tc1[:2]
        return int(float.fromhex(tc2))
  
    def set_temperature(temp_celcius):
        temp = int(temp_celcius*100)
        return "02"+bytearray(struct.pack('<i', temp)[:2]).hex()
  
    def get_temperature(data):
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        result = data[20:]
        status = result[:2]
        if status == "fc":
            return None # device didn't answer, wrong device
        else:  
            tc1 = data[46:]
            tc2 = tc1[:2]
            tc3 = data[48:]
            tc4 = tc3[:2]
            latemp = tc4+tc2
            return float.fromhex(latemp)*0.01
  
    def to_celcius(temp):
        return round((temp-32)*0.5555, 2)

    def from_celcius(temp):
        return round((temp+1.8)+32, 2)
  
    def get_outside_temperature(): #https://api.darksky.net/forecast/{your dark sky key xxxx}/{latitude},{logitude}
        r = requests.get('https://api.darksky.net/forecast/xxxxxxxxxxxxxxxxxxxxxxxx/'+self._latitude+','+self._longitude+'?exclude=minutely,hourly,daily,alerts,flags')
        ledata =r.json()
        return to_celcius(float(json.dumps(ledata["currently"]["temperature"])))
    
    def set_is_away(away): #0=home,2=away
        return "01"+bytearray(struct.pack('<i', away)[:1]).hex()
  
    def get_is_away(data):
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[46:]
        tc2 = tc1[:2]
        return int(float.fromhex(tc2))  

    def set_mode(mode): #0=off,1=freeze protect,2=manual,3=auto,5=away
        return "01"+bytearray(struct.pack('<i', mode)[:1]).hex()
 
    def get_mode(data):
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[46:]
        tc2 = tc1[:2]
        return int(float.fromhex(tc2))
  
    def set_intensity(num):
        return "01"+bytearray(struct.pack('<i', num)[:1]).hex()

    def get_intensity(data):
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[46:]
        tc2 = tc1[:2]
        return int(float.fromhex(tc2))
  
    def get_power_load(data): # get power in watt use by the device
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        result = data[20:]
        status = result[:2]
        if status == "fc":
            return None # device didn't answer, wrong device
        else:     
            tc1 = data[46:]
            tc2 = tc1[:2]
            tc3 = data[48:]
            tc4 = tc3[:2]
            lepower = tc4+tc2
            return int(float.fromhex(lepower))
  
    def set_event_on(num): #1 = light on, 2 = light off, 3 = intensity changed 
        b0 = "10"
        b1 = "00000000"
        b3 = "000000000000000000"
        if num == 1:
            b2 = "020000" #event on = on
        elif num == 2:  
            b2 = "000200" # event off = on
        else:
            b2 = "000002" # event dimmer = on       
        return b0+b1+b2+b3

    def set_timer_on(num): #1 = light on, 2 = light off, 3 = intensity changed 
        b0 = "10"
        b1 = "00000000"
        b3 = "000000000000000000"
        if num == 1:
            b2 = "010000" #event on = timer start
        elif num == 2:
            b2 = "000100" # event off = timer start
        else:
            b2 = "000001" # event dimmer = timer start  
        return b0+b1+b2+b3

    def set_event_off(num): #1 = light on, 2 = light off, 3 = intensity changed 
        b0 = "10"
        b1 = "00000000"
        b3 = "000000000000000000"
        if num == 1:
            b2 = "000000" #event = off
        elif num == 2:
            b2 = "000000" # timer on
        else:
            b2 = "000000" # event = on
        return b0+b1+b2+b3

    def get_event(data): #received event from devices 00100000
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[54:]
        tc2 = tc1[:8]
        return tc2 #int(float.fromhex(tc2))
  
    def set_timer_length(num): # 0=desabled, 1 to 255 lenght on
        return "01"+bytearray(struct.pack('<i', num)[:1]).hex()
  
    def get_timer_length(data): # 0=desabled, 1 to 255 lenght on
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[46:]
        tc2 = tc1[:2]
        return int(float.fromhex(tc2))

    def get_result(data): # check if data write was successfull, return True or False
        sequence = data[12:]
        laseq = sequence[:8]
        dev = data[26:]
        deviceID = dev[:8]
        tc1 = data[20:]
        tc2 = tc1[:2]
        if str(tc2) == "0a": #data read or write
            return True
        elif str(tc2) =="01": #data report
            return True
        return False
  
    def error_info(bug,device):
        if bug == b'FF':
            _LOGGER.debug("in request for %s : Request failed.", device)
        elif bug == b'FE':
            _LOGGER.debug("in request for %s : Buffer full, retry later.", device)
        elif bug == b'FC':
            _LOGGER.debug("in request for %s : Device not responding.", device)
        elif bug == b'FB':
            _LOGGER.debug("in request for %s : Abort failed, request not found in queue.", device)
        elif bug == b'FA':
            _LOGGER.debug("in request for %s : Unknown device or destination deviceID is invalid or not a member of this network.", device)
        else:
            _LOGGER.debug("in request for %s : Unknown error.", device)
        
    def send_request(data):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self._server, PORT)
        sock.connect(server_address)
        try:
            sock.sendall(login_request())
            if binascii.hexlify(sock.recv(1024)) == b'55000c001101000000030000032000009c': #login ok
            sock.sendall(data)
            reply = sock.recv(1024)
            if crc_check(reply):  # receive acknoledge, check status and if we will receive more data
                seq_num = binascii.hexlify(reply)[12:20] #sequence id to link response to the correct request
                deviceid = binascii.hexlify(reply)[26:33]
                status = binascii.hexlify(reply)[20:22]
                more = binascii.hexlify(reply)[24:26] #check if we will receive other data
                if status == b'00': # request status = ok for read and write, we go on (read=00, report=01, write=00)
                    if more == b'01': #GT125 is sending another data response
                        datarec = sock.recv(1024) 
                        return datarec
                elif status == b'01': #status ok for data report
                    return reply
                else:       
                    error_info(status,deviceid)
                    return False
            return reply   
        finally:
            sock.close()

    def send_ping_request(data):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self._server, PORT)
        sock.connect(server_address)
        try:
            sock.sendall(data)
            reply = sock.recv(1024)
            if crc_check(reply):
                return reply
        finally:
            sock.close()
  
    def ping_request():
        ping_data = "550002001200"
        ping_crc = bytes.fromhex(crc_count(bytes.fromhex(ping_data)))
        return bytes.fromhex(ping_data)+ping_crc
      
    def login_request():
        login_data = "550012001001"+self._api_id+self._api_key
        login_crc = bytes.fromhex(crc_count(bytes.fromhex(login_data)))
        return bytes.fromhex(login_data)+login_crc
  
    def get_seq(seq): # could be improuved
        if seq == 0:
            seq = seq_num
        seq += 1  
        return str(seq)  
  
    def count_data(data):
        size = int(len(data)/2)
        return bytearray(struct.pack('<i', size)[:1]).hex()

    def count_data_frame(data):
        size = int(len(data)/2)
        return bytearray(struct.pack('<i', size)[:2]).hex() 
  
    def data_read_request(command,unit_id,data_app): # 21310500 ou FFFFFFFF
        head = "5500"
        data_command = command
        data_seq = get_seq(seq)
        data_type = "00"
        data_res = "000000000000"
        data_dest_id = unit_id
        app_data_size = "04"
        size = count_data_frame(command+data_seq+data_type+data_res+unit_id+app_data_size+data_app)
        data_frame = head+size+command+data_seq+data_type+data_res+unit_id+app_data_size+data_app
        read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
        return bytes.fromhex(data_frame)+read_crc
  
    def data_report_request(command,unit_id,data_app,data): # data = size+time or size+temperature
        head = "5500"
        data_command = command
        data_seq = get_seq(seq)
        data_type = "00"
        data_res = "000000000000"
        data_dest_id = unit_id
        app_data_size = count_data(data_app+data)
        size = count_data_frame(command+data_seq+data_type+data_res+unit_id+app_data_size+data_app+data)
        data_frame = head+size+command+data_seq+data_type+data_res+unit_id+app_data_size+data_app+data
        read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
        return bytes.fromhex(data_frame)+read_crc
  
    def data_write_request(command,unit_id,data_app,data): # data = size+data to send
        head = "5500"
        data_command = command
        data_seq = get_seq(seq)
        data_type = "00"
        data_res = "000000000000"
        data_dest_id = unit_id
        app_data_size = count_data(data_app+data)
        size = count_data_frame(command+data_seq+data_type+data_res+unit_id+app_data_size+data_app+data)
        data_frame = head+size+command+data_seq+data_type+data_res+unit_id+app_data_size+data_app+data
        read_crc = bytes.fromhex(crc_count(bytes.fromhex(data_frame)))
        return bytes.fromhex(data_frame)+read_crc
  
# retreive data from devices

    def get_climate_device_data(self, device_id):
        """Get device data."""
        # Prepare return
        data = {}
        # send requests
        try:
            temperature = get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_temperature))).hex())
            setpoint = get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_setpoint))).hex())
            heatlevel = get_heat_level(bytearray(send_request(data_read_request(data_read_command,device_id,data_heat_level))).hex())
            mode = get_mode(bytearray(send_request(data_read_request(data_read_command,device_id,data_mode))).hex())
            away = get_is_away(bytearray(send_request(data_read_request(data_read_command,device_id,data_away))).hex())
        except OSError:
            raise PySinopeError("Cannot get climate data")
        # Prepare data
        data = "{'setpoint': '"+setpoint+"', 'mode': "+mode+", 'alarm': 0, 'rssi': 0, 'temperature': "+temperature+", 'heatLevel': "+heatlevel+", 'away': "+away+"}"
        return data

    def get_light_device_data(self, device_id):
        """Get device data."""
        # Prepare return
        data = {}
        # send requests
        try:
            intensity = get_intensity(bytearray(send_request(data_read_request(data_read_command,device_id,data_light_intensity))).hex())
            mode = get_mode(bytearray(send_request(data_read_request(data_read_command,device_id,data_light_mode))).hex())
        except OSError:
            raise PySinopeError("Cannot get light data")
        # Prepare data
        data = "{'intensity': '"+intensity+"', 'mode': "+mode+", 'alarm': 0, 'rssi': 0}"
        return data

    def get_switch_device_data(self, device_id):
        """Get device data."""
        # Prepare return
        data = {}
        # send requests
        try:
            intensity = get_intensity(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_intensity))).hex())
            mode = get_mode(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_mode))).hex())
            powerwatt = get_power_load(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_connected))).hex())
        except OSError:
            raise PySinopeError("Cannot get switch data")
        # Prepare data
        data = "{'intensity': '"+intensity+"', 'mode': "+mode+", 'powerWatt': "+powerwatt+", 'alarm': 0, 'rssi': 0}"
        return data

    def get_climate_device_info(self, device_id):
        """Get information for this device."""
        # Prepare return
        data = {}
        # send requests
        try:
            tempmax = get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_max_temp))).hex())
            tempmin = get_temperature(bytearray(send_request(data_read_request(data_read_command,device_id,data_min_temp))).hex())
            wattload = get_power_load(bytearray(send_request(data_read_request(data_read_command,device_id,data_load))).hex())
            wattoveride = get_power_load(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_connected))).hex())
        except OSError:
            raise PySinopeError("Cannot get climate info")    
        # Prepare data
        data = "{'active': 1, 'tempMax': "+tempmax+", 'tempMin': "+tempmin+", 'wattage': "+wattload+", 'wattageOverride': "+wattoveride+"}"
        return data

    def get_light_device_info(self, device_id):
        """Get information for this device."""
        # Prepare return
        data = {}
        # send requests
        try:
            timer = get_timer_lenght(bytearray(send_request(data_read_request(data_read_command,device_id,data_light_timer))).hex())
        except OSError:
            raise PySinopeError("Cannot get light info")    
        # Prepare data
        data = "{'active': 1, 'timer': "+timer+"}"
        return data

    def get_switch_device_info(self, device_id):
        """Get information for this device."""
        # Prepare return
        data = {}
        # send requests
        try:
            wattload = get_power_load(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_load))).hex())
            timer = get_timer_lenght(bytearray(send_request(data_read_request(data_read_command,device_id,data_power_timer))).hex())
        except OSError:
            raise PySinopeError("Cannot get switch info")    
        # Prepare data
        data = "{'active': 1, 'wattage': "+wattload+", 'timer': "+timer+"}"
        return data

    def set_brightness(self, device_id, brightness):
        """Set device intensity."""
        try:
            result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_light_intensity,set_intensity(brightness)))).hex())
        except OSError:
            raise PySinopeError("Cannot set device brightness")
        return result

    def set_mode(self, device_id, device_type, mode):
        """Set device operation mode."""
        # prepare data
        try:
            if device_type < 100:
                result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_mode,set_mode(mode)))).hex())
            else:
                result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_light_mode,set_mode(mode)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device operation mode")
        return result
      
    def set_is_away(self, device_id, away):
        """Set device away mode."""
        try:
            if device_id == "all":
                device_id = "FFFFFFFF"
                result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_away,set_is_away(away)))).hex())
            else:    
                result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_away,set_is_away(away)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device away mode")
        return result 
      
    def set_temperature(self, device_id, temperature):
        """Set device temperature."""
        try:
            result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_setpoint,set_temperature(temperature)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device setpoint temperature")
        return result
      
    def set_timer(self, device_id, timer_length):
        """Set device timer length."""
        try:
            result = get_result(bytearray(send_request(data_write_request(data_write_command,device_id,data_light_timer,set_timer_length(timer_length)))).hex())
        except OSError:
            raise PyNeviwebError("Cannot set device timer length")
        return result      

    def set_report(self, device_id):
        """Set report to send data to each devices"""
        try:
            result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_time,set_time()))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_date,set_date()))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_sunrise,set_sun_time("sunrise")))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_sunset,set_sun_time("sunset")))).hex())
            if result == False:
                return result
            result = get_result(bytearray(send_request(data_report_request(data_report_command,device_id,data_outdoor_temperature,set_temperature(get_outside_temperature())))).hex())
        except OSError:
            raise PyNeviwebError("Cannot send report to each devices")
        return result
