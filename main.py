# on-board goodies
import sys
import os
import gc
import uasyncio
from hashlib import sha1
import urequests as requests
from time import sleep, gmtime, localtime
import network
import ntptime
from machine import Pin, SPI, reset

sys.path.append("/include")
# external things
from ili9341 import Display, color565
import hmac
import base64
import md5

# Global variables so it can be persistent
solar_usage = {}
# led_bright = 800
CRED_FILE = "config/credentials.env"
SOLIS_FILE = "config/solis.env"

day_btn = Pin(35, Pin.IN, Pin.PULL_UP)
reset_btn = Pin(36, Pin.IN, Pin.PULL_UP)


# Local time doings
def stringTime(thisTime):
    year, month, date, hour, minute, second, week_day, year_day = thisTime
    week_day_lookup = b"MonTueWedThuFriSatSun"
    month_lookup = b"JanFebMarAprMayJunJulAugSepOctNovDec"
    stringTime = (
        week_day_lookup.decode()[week_day * 3 : week_day * 3 + 3]
        + ", "
        + f"{date:02}"
        + " "
        + month_lookup.decode()[(month - 1) * 3 : (month - 1) * 3 + 3]
        + " "
        + f"{year:02}"
        + " "
        + f"{hour:02}"
        + ":"
        + f"{minute:02}"
        + ":"
        + f"{second:02}"
        + " GMT"
    )
    return stringTime


def getSolis(solisInfo):
    solar_dict = {}
    url = solisInfo["solisUrl"]
    CanonicalizedResource = solisInfo["solisPath"]

    req = url + CanonicalizedResource
    VERB = "POST"
    Content_Type = "application/json"

    Date = stringTime(gmtime())

    Body = (
        '{"pageSize":100,  "id": "'
        + solisInfo["solisId"].decode()
        + '", "sn": "'
        + solisInfo["solisSn"].decode()
        + '" }'
    )
    Content_MD5 = base64.b64encode(md5.digest(Body.encode("utf-8"))).decode("utf-8")
    encryptStr = (
        VERB
        + "\n"
        + Content_MD5
        + "\n"
        + Content_Type
        + "\n"
        + Date
        + "\n"
        + CanonicalizedResource
    )
    h = hmac.new(
        solisInfo["solisSecret"].decode().encode("utf-8"),
        msg=encryptStr.encode("utf-8"),
        digestmod=sha1,
    )
    Sign = base64.b64encode(h.digest())
    Authorization = "API " + solisInfo["solisKey"].decode() + ":" + Sign.decode("utf-8")

    header = {
        "Content-MD5": Content_MD5,
        "Content-Type": Content_Type,
        "Date": Date,
        "Authorization": Authorization,
    }
    solar_text = ""
    solar_resp = "!!!"
    try:
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
        print("\n\nPOST to " + url + "...", end="")
        resp = requests.post(req, data=Body, headers=header, timeout=60)
        print("[" + str(resp.status_code) + "]")
        solar_text = resp.text
        solar_resp = resp.status_code
    except Exception as e:
        print("get solar_usage didn't work sorry because this: " + str(e))

    solar_dict = {"resp": solar_resp}

    if solar_text != "":
        for each_field in solar_text.split(","):
            if '"dataTimestamp":' in each_field:
                solar_dict["timestamp"] = each_field.split(":")[1]
            if '"pac":' in each_field:
                solar_dict["solar_in"] = each_field.split(":")[1]
            if '"batteryCapacitySoc":' in each_field:
                solar_dict["battery_per"] = each_field.split(":")[1]
            if '"psum":' in each_field:
                solar_dict["grid_in"] = each_field.split(":")[1]
            if '"familyLoadPower":' in each_field:
                solar_dict["power_used"] = each_field.split(":")[1]
            if '"eToday":' in each_field:
                solar_dict["solar_today"] = each_field.split(":")[1]
    return solar_dict


# Coroutine: get the solis data every 45 seconds
def display_data(solar_usage, display, force=False):
    # Sanity check printing business
    print("solis timestamp is: " + solar_usage["timestamp"])
    print("solar_in is: " + solar_usage["solar_in"])
    print("battery_per is: " + solar_usage["battery_per"])
    print("grid_in is: " + solar_usage["grid_in"])
    print("power_used is: " + solar_usage["power_used"])
    print("solar_today is: " + solar_usage["solar_today"] + "\n")
    if force or (solar_usage["timestamp"] != solar_usage["prev_timestamp"]):
        print("Solis data has been updated - do the LCD thing...")


async def timer_solis_data(solisInfo, display):
    global solar_usage
    solar_usage["prev_battery_int"] = 0
    solar_usage["prev_timestamp"] = "0"
    while True:
        solar_dict = getSolis(solisInfo)
        if "timestamp" in solar_dict:
            solar_usage.update(solar_dict)
            display_data(solar_usage, display)
            # ready to loop then
            solar_usage["prev_battery_int"] = int(float(solar_usage["battery_per"]))
            solar_usage["prev_timestamp"] = solar_usage["timestamp"]
        else:
            print("No data returned")
            if "resp" in solar_dict:
                solar_usage["resp"] = solar_dict["resp"]
        await uasyncio.sleep(45)


# Coroutine: reset button
async def wait_reset_button():
    global CRED_FILE
    btn_count = 0
    btn_max = 75
    while True:
        if reset_btn.value() == 1:
            btn_count = 0
        if reset_btn.value() == 0:
            print(f"Pressed - count is {str(btn_count)}")
            btn_count = btn_count + 1
        if btn_count >= btn_max:
            sleep(2)
            os.remove(CRED_FILE)
            reset()
        await uasyncio.sleep(0.04)


# Coroutine: day button press
async def wait_day_button(day_btn):
    btn_prev = day_btn.value()
    while (day_btn.value() == 1) or (day_btn.value() == btn_prev):
        btn_prev = day_btn.value()
        await uasyncio.sleep(0.04)


# Corouteine: display solar today
async def display_solar_today(display):
    if "solar_today" in solar_usage:
        print("Solar today is " + solar_usage["solar_today"])
        print("Last updated: " + solar_usage["timestamp"])
        # lcd_line(lcd, "Today: " + solar_usage["solar_today"][:4] + "kW")
        solis_time = stringTime(
            localtime(int(float(solar_usage["timestamp"].replace('"', "")) / 1000))
        )[-12:].replace("GMT", "UTC")
        # lcd_line(lcd, "at " + solis_time, 1)
    else:
        if "resp" in solar_usage:
            print("No Solar today data - oops")
            print(f"last response code: {solar_usage['resp']}")
            # lcd_line(lcd, "solis response:")
            # lcd_line(lcd, str(solar_usage["resp"]), 1)
    await uasyncio.sleep(5)
    # put the old data back
    if "timestamp" in solar_usage:
        display_data(solar_usage, display, True)
    print("And I'm done.")


async def main():
    spi1 = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
    display = Display(spi1, dc=Pin(2), cs=Pin(15), rst=Pin(0))

    solisInfo = {}
    # Now separate credentials
    global CRED_FILE
    global SOLIS_FILE

    try:
        with open(CRED_FILE, "rb") as f:
            contents = f.read().split(b",")
            if len(contents) == 6:
                (
                    solisInfo["wifiSSID"],
                    solisInfo["wifiPass"],
                    solisInfo["solisKey"],
                    solisInfo["solisSecret"],
                    solisInfo["solisId"],
                    solisInfo["solisSn"],
                ) = contents
    except OSError:
        print("No or invalid credentials file - please reset and start again")
        sys.exit()

    f = open("config/solis.env")
    for line in f:
        if "=" in line:
            thisAttr = line.strip().split("=")[0]
            thisVal = line.strip().split("=")[1]
            solisInfo[thisAttr] = thisVal
    f.close()

    # Configure the network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting", end="")
    # lcd_line(lcd, "Connecting to")
    # lcd_line(lcd, "WiFi ...", 1)
    wlan.connect(solisInfo["wifiSSID"], solisInfo["wifiPass"])
    ipAddress, netMask, defaultGateway, DNS = wlan.ifconfig()
    wifiCount = 0
    while ipAddress == "0.0.0.0" and wifiCount < 30:
        print(".", end="")
        await uasyncio.sleep(1)
        ipAddress, netMask, defaultGateway, DNS = wlan.ifconfig()
        wifiCount += 1

    if ipAddress == "0.0.0.0":
        print("No WiFi connection - please check details in solis.env")
        sys.exit()

    print("Wifi connected - IP address is: " + ipAddress)
    # lcd_line(lcd, "Connected. SSID:")
    # lcd_line(lcd, solisInfo["wifiSSID"].decode(), 1)
    await uasyncio.sleep(2)
    # lcd_line(lcd, "Connected. IP:")
    # lcd_line(lcd, ipAddress, 1)

    ntptime.host = "0.uk.pool.ntp.org"
    ntptime.settime()

    # Main loop
    # Get the solis data

    uasyncio.create_task(timer_solis_data(solisInfo, display))
    uasyncio.create_task(wait_reset_button())

    while True:
        await wait_day_button(day_btn)
        await display_solar_today(display)


if __name__ == "__main__":
    try:
        # Start event loop and run entry point coroutine
        uasyncio.run(main())
    except KeyboardInterrupt:
        pass
