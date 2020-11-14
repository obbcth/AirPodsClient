from bleak import discover
from time import time,sleep
from infi.systray import SysTrayIcon
import asyncio, threading, webbrowser
import win32api
import sys, os

# https://stackoverflow.com/questions/20602727/pyinstaller-generate-exe-file-folder-in-onefile-mode
# Thanks!

def on_quit_callback(systray):
    sys.exit()

def app_path(path):
    frozen = 'not'
    if getattr(sys, 'frozen', False):
            # we are running in executable mode
            frozen = 'ever so'
            app_dir = sys._MEIPASS
    else:
            # we are running in a normal Python environment
            app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, path)

def open_homepage(systray):
    webbrowser.open('https://github.com/obbcth/AirPodsClient', new=2)

BAT = True

def switch_tray(systray):
    global BAT
    if BAT:
        BAT = False
    else:
        BAT = True

AED = False # Automatic Ear Detection
AED_Flag = True

def automatic_ear_detection(systray):
    global AED 
    if AED:
        menu_options = (
            ("Visit GitHub", None, open_homepage),
            ("(Experimental) Automatic Ear Detection : Off", None, automatic_ear_detection),
            ("Switch Tray Icon", None, switch_tray),
        )
        AED = False
    else:
        menu_options = (
            ("Visit GitHub", None, open_homepage),
            ("(Experimental) Automatic Ear Detection : On", None, automatic_ear_detection),
            ("Switch Tray Icon", None, switch_tray),
        )
        AED = True
    systray.update(menu_options = menu_options)


menu_options = (
    ("Visit GitHub", None, open_homepage),
    ("(Experimental) Automatic Ear Detection : Off", None, automatic_ear_detection),
    ("Switch Tray Icon", None, switch_tray),
)


systray = SysTrayIcon(app_path("icons/AirPods.ico"), "Scanning devices...", menu_options, on_quit=on_quit_callback)

systray.start()



def icon_update(result):
    global systray, status

    if BAT:
        
        if result['left'] == -1 and result['right'] == -1:
            value = 0
        elif result['left'] == -1:
            value = result['right'] // 10
        elif result['right'] == -1:
            value = result['left'] // 10
        else:
            value = (result['left'] + result['right']) // 2 // 10
        if value == 3:
            value = 2
        if value == 4:
            value = 3
        if value == 5 or value == 6:
            value = 4
        if value == 7:
            value = 5
        if value == 8 or value == 9:
            value = 6
        if value == 10:
            value = 7
        if value == 0:
            value = ""

        if result['model'] == "Pro":
            systray.update(app_path("icons/AirPodsPro" + str(value) + ".ico"), status)

        if result['model'] == "Unknown":
            systray.update(app_path("icons/AirPods" + str(value) + ".ico"), status)
    else:
        if result['model'] == "Pro":
            systray.update(app_path("icons/AirPodsPro.ico"), status)

        if result['model'] == "Unknown":
            systray.update(app_path("icons/AirPods.ico"), status)



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
            result['status'] = 1

            # 12th and 13th letter shows:
            # the charge of the left and right pods. Under unknown circumstances, they are right and left instead (see isFlipped). Values between 0 and 10 are battery 0-100%; Value 15 means it's disconnected
            flipped = isFlipped(hexData)
            if flipped:
                result['left'] = "" + hexData[12]
                result['right'] = "" + hexData[13]
            else:
                result['left'] = "" + hexData[13]
                result['right'] = "" + hexData[12]

            # 15th letter shows:
            # the charge of the case. Values between 0 and 10 are battery 0-100%; Value 15 means it's disconnected
            result['case'] = "" + hexData[15]

            # 14th letter shows:
            # the "in charge" status. Bit 0 (LSB) is the left pod; Bit 1 is the right pod; Bit 2 is the case. Bit 3 might be case open/closed but I'm not sure and it's not used
            result['charging_case'] = "" + hexData[14]
            result['charging_left'] = "" + hexData[14]
            result['charging_right'] = "" + hexData[14]

            # 7th letter shows:
            # the AirPods model (E=AirPods pro)
            result['model'] = "" + hexData[7]

            # 11th letter shows:
            # 1 when both AirPods are removed from ears
            # b when both AirPods are in ears
            # 3 (Left Plugged) or 9 (Right Plugged) when only one AirPod is removed
            # 2 when one AirPod is in the case charging and other one is in ear
            # 0 when one AirPod is in the case charging and other one is not in ear
            result['wearing'] = "" + hexData[11]

            # 21th letter shows: 
            # 5 when playing
            # 4 when paused
            result['playing'] = "" + hexData[21]

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

    result['wearing'] = int(result['wearing'], 16)
    if result['wearing'] != 11:
        result['wearing'] = 0
    else:
        result['wearing'] = 1
    
    result['playing'] = int(result['playing'], 16) - 4

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
    result['wearing'] = 0
    result['playing'] = 0
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

    icon_update(result)
    
    if AED:
        if result['wearing'] == 0:
            if AED_Flag:
                win32api.keybd_event(0xB3, 34)
                AED_Flag = False

        if result['wearing'] == 1:
            if AED_Flag == False:
                win32api.keybd_event(0xB3, 34)
                AED_Flag = True
    
