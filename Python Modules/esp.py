import requests
import webiopi

LEFT_LIGHT_PIN = "13"
RIGHT_LIGHT_PIN = "12"
TV_HIFI_PIN = "4"


class Api():

	def __init__(self,address):
		self.address = str(address)
		try:
			resp = requests.get(self.address)
			if resp.status_code != 200:
				webiopi.debug("can't get status from api")
		except:
			webiopi.debug("connection error at init")
			

	def get_status(self,function,pin):
		function = str(function) 
		if pin == "left_light":
			pin = LEFT_LIGHT_PIN
		elif pin == "tv-hifi":
			pin = TV_HIFI_PIN
		elif pin == "right_light":
			pin = RIGHT_LIGHT_PIN
		pin = str(pin)
		try:
			resp = requests.get(self.address + "/" + function + "/" + pin,timeout=0.0a1)
			if resp.status_code !=200:
				webiopi.debug("can't get status from api")
			answer = resp.json()
			return 1 - int(answer["return_value"]) #invert logic
		except:
			webiopi.debug("connection error with get_status")
			return 0  #json data is string, "1"--> int 1 --> true/false
	
	def set_status(self,function,pin,status):
		function = str(function)
		pin = str(pin)
		status = 1 - status #invert logic
		status = str(status)
		webiopi.debug("set status is :"+status)

		if pin == "left_light":
			pin = LEFT_LIGHT_PIN
		elif pin == "tv-hifi":
			pin = TV_HIFI_PIN
		elif pin == "right_light":
			pin = RIGHT_LIGHT_PIN
		try:
			resp = requests.get(self.address + "/" + function + "/" + pin + "/" + status)
			answer = resp.json()
			return int(answer["return_value"])
		except:
			webiopi.debug("connection error with set_status")
			return 0

	def turn_on_pc(self):
		try:
			resp = requests.post(self.address+"/pc_on?params=0")
		except:
			webiopi.debug("connection error with turn_on_pc")
			return 0

		