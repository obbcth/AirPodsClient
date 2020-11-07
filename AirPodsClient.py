from bleak import discover
from time import time,sleep
from infi.systray import SysTrayIcon
import asyncio, threading, bluetooth, webbrowser

def open_homepage(systray):
    webbrowser.open('https://github.com/obbcth/AirPodsClient', new=2)

menu_options = (("Visit GitHub", None, open_homepage),)
systray = SysTrayIcon("white.ico", "Scanning devices...", menu_options)
systray.start()

async def run():
    result = EmptyResult()
    devices = await discover()

    for d in devices:
        try:
            if not 76 in d.metadata['manufacturer_data']:
                continue
            if not len(d.metadata['manufacturer_data'][76]) == 27:
                continue

            if result['status'] == 1 and result['rssi'] > d.rssi:
                continue

            result['rssi'] = d.rssi
            result['addr'] = d.address
            
            hexData = d.metadata['manufacturer_data'][76].hex()
            flipped = isFlipped(hexData)
            if flipped:
                result['left'] = "" + hexData[12]
                result['right'] = "" + hexData[13]
            else:
                result['left'] = "" + hexData[13]
                result['right'] = "" + hexData[12]
            result['case'] = "" + hexData[15]
            result['charging_case'] = "" + hexData[14]
            result['charging_left'] = "" + hexData[14]
            result['charging_right'] = "" + hexData[14]
            result['model'] = "" + hexData[7]
            result['status'] = 1

            result = parseValues(result, flipped)

        except Exception as ex:
            result = EmptyResult()
            result["error"] = str(ex)

    return result

def isFlipped(data):
    return format((int(""+data[10], 16)+(0x10)), 'b')[3] == '0'

def parseValues(result, flipped):
    if result['model'] == 'e': 
        result['model'] = "Pro"
    else:
        result['model'] = "Unknown"

    result['left'] = int(result['left'], 16) * 10
    result['right'] = int(result['right'], 16) * 10
    result['case'] = int(result['case'], 16) * 10

    if result['left'] > 100:
        result['left'] = -1

    if result['right'] > 100:
        result['right'] = -1

    if result['case'] > 100:
        result['case'] = -1

    chargeStatus = int(result['charging_case'], 16) # Charge status sometimes changed between left and right.
    if flipped:
        result['charging_left'] = (chargeStatus & 0b00000001) != 0
        result['charging_right'] = (chargeStatus & 0b00000010) != 0
    else:
        result['charging_left'] = (chargeStatus & 0b00000001) != 0
        result['charging_right'] = (chargeStatus & 0b00000010) != 0
    result['charging_case'] = (chargeStatus & 0b00000100) != 0 # Only right value returns when AirPods are in case.

    return result

def EmptyResult():
    result = {}
    result["status"] = 0
    result['left'] = -1
    result['right'] = -1
    result['case'] = -1
    result['charging_case'] = False
    result['charging_left'] = False
    result['charging_right'] = False
    result["error"] = ""
    result["rssi"] = -670
    result["addr"] = ""
    result['model'] = ""
    return result

def fetch_status():
    loop = asyncio.new_event_loop()
    data = loop.run_until_complete(run())
    loop.close()
    return data

while True:
    result = fetch_status()
    
    status = "L: " + str(result['left']) + str(result['charging_left']) + " / R: " + str(result['right']) + str(result['charging_right']) + " / C: " + str(result['case']) + str(result['charging_case'])
    
    status = status.replace('-1', '?')
    status = status.replace('True', '+')
    status = status.replace('False', '')

    if result['model'] == "Pro":
        systray.update("lightblue.ico", status)

    if result['model'] == "Unknown":
        systray.update("lightgreen.ico", status)
    
