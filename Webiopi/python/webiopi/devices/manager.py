import imp
import os.path
import json as JSON
from time import sleep, time
from webiopi.utils import logger
from webiopi.utils import types
from webiopi.utils.config import Config
from webiopi.devices import serial, digital, analog, sensor, shield
from webiopi.devices.instance import DEVICES
from webiopi.devices.onewire import detectOneWireDevices

PACKAGES = [serial, digital, analog, sensor, shield]
DYNAMIC_DEVICES  = {}
DEVICES_JSON_FILE = "/etc/webiopi/devices.json"
def deviceDetector():
    logger.debug('deviceDetector')
    try:
        devices = detectOneWireDevices()
        for dev in devices:
            found = False
            for DEV in DEVICES:
                if 'slave' in DEVICES[DEV]['args']:
                    if DEVICES[DEV]['args']['slave'] == dev['args']['slave']:
                        logger.debug('Device found: ' +  dev['args']['slave'])
                        found = True
            if not found:
                if addDevice(dev['name'], dev['device'], dev['description'], dev['args'], "auto") > 0:
                    saveDevice(dev['name'])
    except Exception as e:
        logger.error("Device detector: %s" % e)

    sleep(5)

def findDeviceClass(name):
    for package in PACKAGES:
        if hasattr(package, name):
            return getattr(package, name)
        if hasattr(package, "DRIVERS"):
            for driver in package.DRIVERS:
                if name in package.DRIVERS[driver]:
                    (fp, pathname, stuff) = imp.find_module(package.__name__.replace(".", "/") + "/" + driver)
                    module = imp.load_module(driver, fp, pathname, stuff)
                    return getattr(module, name)
    return None

def saveDevice(name):
    logger.debug('saveDevice: ' + str(name))
    if name not in DEVICES:
        return
    #never save to json devices that are manually added
    if DEVICES[name]['origin'] == 'manual':
        return
    DYNAMIC_DEVICES[name] = DEVICES[name]
    json_devices = getJSON(DYNAMIC_DEVICES)
    with open(DEVICES_JSON_FILE, 'w') as outfile:
        outfile.write(json_devices)

def removeDevice(name):
    if name in DEVICES:
        if name in DYNAMIC_DEVICES:
            if hasattr(DEVICES[name]["device"], 'close'):
                    DEVICES[name]["device"].close()
            del DEVICES[name]
            del DYNAMIC_DEVICES[name]
            json_devices = getJSON(DYNAMIC_DEVICES)
            with open(DEVICES_JSON_FILE, 'w') as outfile:
                outfile.write(json_devices)
            logger.debug("Deleted device %s" % name)
            return (200, None, None)
        logger.error("Cannot delete %s, found but not added via REST" % name)
        return (403, None, None)
    logger.error("Cannot delete %s, not found" % name)
    return (404, None, None)


def addDeviceJSON(json):
    if "name" in json:
        name = json["name"]
    else:
        name = "%X" % time()
    device = json["device"]

    if 'args' in json:
        args = json["args"]
    else:
        args = []

    if 'description' in json:
        description = json["description"]
    else:
        description = name

    res = addDevice(name, device, description, args, "rest")
    if res == 1:
        saveDevice(name)
        return (200, "OK", "text/plain")
    elif res == -1:
        return (200, "ALREADY_EXISTS", "text/plain")
    elif res == 0:
        return (200, "ERROR", "text/plain")

def updateDevice(name, json):
    if not name in DEVICES:
        return (404, None, None)

    if "name" in json:
#       forbid name changed
#        if json["name"] != name:
#            return (403, "FORBIDDEN", "text/plain")

        if json["name"] != name and json["name"] in DEVICES:
            return (403, "ALREADY_EXISTS", "text/plain")

    logger.info("Edit %s" % name)
    (c, d, t) = removeDevice(name)
    if c == 200:
        (c, d, t) = addDeviceJSON(json)
    
    return (c, d, t)


def addDevice(name, device, description, args, origin):
    if name in DEVICES:
        logger.error("Device <%s> already exists" % name)
        return -1
    logger.debug('addDevice: ' + str(name))
#    if '/' in device:
#        deviceClass = device.split('/')[0]
#    else:
#        deviceClass = device
    
    constructor = findDeviceClass(device)

    if constructor == None:
        raise Exception("Device driver not found for %s" % device)
    
    instance = None
    try:
        if len(args) > 0:
            instance = constructor(**args)
        else:
            instance = constructor()
        addDeviceInstance(name, device, description, instance, args, origin)
        return 1
    except Exception as e:
        logger.error("Error while adding device %s(%s) : %s" % (name, device, e))
        if origin == "manual":
            addDeviceInstance(name, device, description, None, args, "manual")
        
    return 0

def addDeviceConf(devices, origin):
    for (name, params) in devices:
        values = params.split(" ")
        driver = values[0];
        description = name
        args = {}
        i = 1
        while i < len(values):
            (arg, val) = values[i].split(":")
            args[arg] = val
            i+=1
        addDevice(name, driver, description, args, origin)
        saveDevice(name)

def loadJsonDevices(origin):
    import os.path
    if os.path.isfile(DEVICES_JSON_FILE):
        with open(DEVICES_JSON_FILE, encoding='utf-8') as data_file:
            json_devices = JSON.loads(data_file.read())
            for device in json_devices:
                addDevice(device['name'], device['device'], device['description'], device['args'], origin)
                if device['name'] in DEVICES:
                    DYNAMIC_DEVICES[device['name']] = DEVICES[device['name']]

def addDeviceInstance(name, device, description, instance, args, origin):
    funcs = {"GET": {}, "POST": {}}
    families = []   
    if (instance != None):
        for att in dir(instance):
            func = getattr(instance, att)
            if callable(func) and hasattr(func, "routed"):
                if name == "GPIO":
                    logger.debug("Mapping %s.%s to REST %s /GPIO/%s" % (instance, att, func.method, func.path))
                else:
                    logger.debug("Mapping %s.%s to REST %s /devices/%s/%s" % (instance, att, func.method, name, func.path))
                funcs[func.method][func.path] = func
    
        if hasattr(instance, "__family__"):
            family = instance.__family__()
            if isinstance(family, str):
                families.append(family)
            else:
                for fam in family:
                    families.append(fam)
        else:
            families.append(instance.__str__())
   
        if name == "GPIO":
            logger.info("GPIO - Native mapped to REST API /GPIO")
        else:
            logger.info("%s - %s mapped to REST API /devices/%s" % (instance.__family__(), instance, name))

    DEVICES[name] = {
        'class'       : device,
        'device'      : instance,
        'description' : description,
        'args'        : args,
        'type'        : families,
        'status'      : 1 if instance != None else 0,
        'functions'   : funcs,
        'origin'      : origin
    }
        
def closeDevices():
    devices = [k for k in DEVICES.keys()]
    for name in devices:
        device = DEVICES[name]["device"]
        logger.debug("Closing device %s - %s" %  (name, device))
        del DEVICES[name]
        if hasattr(device, 'close'):
            device.close()

def getDevicesJSON(compact=False):
    return getJSON(DEVICES, compact)

def getJSON(devices_list, compact = False):
    devices = []
    for name in devices_list:
        if name == "GPIO":
            continue
        
        dev = devices_list[name]
        devices.append({
            'name' : name,
            'description': dev['description'],
            'device' : dev['class'],
            'type' : dev['type'],
            'status': dev['status'],
            'args' : dev['args'],
            'origin' : dev['origin']
        })

    return types.jsonDumps(sorted(devices, key=lambda dev: dev['name']))
