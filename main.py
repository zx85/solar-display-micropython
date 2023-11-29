# on-board goodies
import sys
import gc
import json
import uasyncio
from hashlib import sha1
import urequests as requests
from time import sleep, gmtime
import network
import ntptime
from machine import Pin, I2C

sys.path.append("/include")
# external things
from machine_i2c_lcd import I2cLcd
import hmac
import base64
import md5

# Global variable so it can be persistent
solar_usage = {}


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
    solar = {}
    url = solisInfo["solisUrl"]
    CanonicalizedResource = solisInfo["solisPath"]

    req = url + CanonicalizedResource
    VERB = "POST"
    Content_Type = "application/json"

    Date = stringTime(gmtime())

    Body = (
        '{"pageSize":100,  "id": "'
        + solisInfo["solisId"]
        + '", "sn": "'
        + solisInfo["solisSn"]
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
        solisInfo["solisSecret"].encode("utf-8"),
        msg=encryptStr.encode("utf-8"),
        digestmod=sha1,
    )
    Sign = base64.b64encode(h.digest())
    Authorization = "API " + solisInfo["solisKey"] + ":" + Sign.decode("utf-8")

    header = {
        "Content-MD5": Content_MD5,
        "Content-Type": Content_Type,
        "Date": Date,
        "Authorization": Authorization,
    }

    try:
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
        print("\n\nPOST to " + url + "...", end="")
        resp = requests.post(req, data=Body, headers=header, timeout=60)
        print("[" + str(resp.status_code) + "]")
        solar = resp.text
    except Exception as e:
        print("get solar_usage didn't work sorry because this: " + str(e))

    return solar


# Coroutine: get the solis data every 45 seconds
async def display_data(solisInfo, lcd):
    global solar_usage
    # do something funny with the battery icon ha
    battery_icon = bytearray([0x0E, 0x0E, 0x11, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F])
    prev_battery_int = 0
    prev_timestamp = 0
    while True:
        solar = getSolis(solisInfo)
        print(solar[:30])
        if "groovydata" in solar:
            solar_usage = solar
            timestamp = solar_usage["data"]["dataTimestamp"]
            solar_in = str(solar_usage["data"]["pac"])
            battery_per = str(solar_usage["data"]["batteryCapacitySoc"])
            battery_int = int(float(battery_per))
            grid_in = str(solar_usage["data"]["psum"])
            grid_float = float(grid_in)
            power_used = str(solar_usage["data"]["familyLoadPower"])
            solar_today = str(solar_usage["data"]["eToday"])
            # Sanity check printing business
            print("solis timestamp is: " + timestamp)
            print("solar_in is: " + solar_in)
            print("battery_per is: " + battery_per)
            print("grid_in is: " + grid_in)
            print("power_used is: " + power_used)
            print("solar_today is: " + solar_today + "\n")
            if timestamp != prev_timestamp:
                print("Solis data has been updated - do the LCD thing...")
                # LCD business
                if battery_int < 90:
                    battery_icon[1] = 0x0A
                if battery_int < 75:
                    battery_icon[2] = 0x11
                if battery_int < 60:
                    battery_icon[3] = 0x11
                if battery_int < 45:
                    battery_icon[4] = 0x11
                if battery_int < 30:
                    battery_icon[5] = 0x11
                if battery_int < 15:
                    battery_icon[6] = 0x11
                lcd.custom_char(5, battery_icon)
                lcd.clear()
                lcd.hide_cursor()
                # Solar
                lcd.move_to(0, 0)
                lcd.putstr(chr(0) + " " + solar_in[:4] + "kW      ")
                # Battery
                lcd.move_to(9, 0)
                lcd.putstr(chr(5))
                if battery_int == prev_battery_int:
                    lcd.putstr("=")
                if battery_int < prev_battery_int:
                    lcd.putstr(chr(4))
                if battery_int > prev_battery_int:
                    lcd.putstr(chr(3))
                lcd.putstr(" " + str(battery_int) + "%     ")
                # Grid
                lcd.move_to(0, 1)
                lcd.putstr(chr(1))
                if grid_float == 0:
                    lcd.putstr("=0kW   ")
                if grid_float < 0:
                    lcd.putstr(chr(4) + grid_in[1:5] + "kW    ")
                if grid_float > 0:
                    lcd.putstr(chr(3) + grid_in[:4] + "kW    ")
                # Usage
                lcd.move_to(9, 1)
                lcd.putstr(
                    chr(2) + power_used[:4] + "kW" + " " * (4 - len(power_used[:4]))
                )
            # ready to loop then
            prev_battery_int = battery_int
            prev_timestamp = timestamp
        else:
            print("No data returned")
        await uasyncio.sleep(45)


# Coroutine: button press
async def wait_button(btn):
    btn_prev = btn.value()
    while (btn.value() == 1) or (btn.value() == btn_prev):
        btn_prev = btn.value()
        await uasyncio.sleep(0.04)


# Corouteine: display solar today
async def display_solar_today(lcd):
    if "data" in solar_usage:
        print("Solar today is " + solar_usage["data"]["eToday"])
        print("Last updated: " + solar_usage["data"]["dataTimestamp"])
    else:
        print("No Solar today data - sorry")
    await uasyncio.sleep(5)
    print("And I'm done.")


async def main():
    # define the display
    # WEMOS LOLIN32 ESP32 Lite pinout
    sdaPIN = Pin(23)
    sclPIN = Pin(19)
    # S2MINI pinout (I think)
    # sdaPIN = Pin(33)
    # sclPIN = Pin(35)
    i2c = I2C(0, sda=sdaPIN, scl=sclPIN, freq=400000)
    devices = i2c.scan()
    for device in devices:
        print("i2c address is" + hex(device))
    I2C_ADDR = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    btn = Pin(35, Pin.IN, Pin.PULL_UP)

    # Custom character bits
    solar_icon = bytearray([0x00, 0x15, 0x0E, 0x1F, 0x1F, 0x0E, 0x15, 0x00])
    lcd.custom_char(0, solar_icon)
    grid_icon = bytearray([0x07, 0x0E, 0x18, 0x1F, 0x07, 0x0E, 0x0C, 0x10])
    lcd.custom_char(1, grid_icon)
    mains_icon = bytearray([0x00, 0x0A, 0x0A, 0x1F, 0x1F, 0x0E, 0x04, 0x1C])
    lcd.custom_char(2, mains_icon)
    up_icon = bytearray([0x04, 0x0E, 0x1B, 0x11, 0x00, 0x00, 0x00, 0x00])
    lcd.custom_char(3, up_icon)
    down_icon = bytearray([0x00, 0x00, 0x00, 0x00, 0x11, 0x1B, 0x0E, 0x04])
    lcd.custom_char(4, down_icon)

    # TODO: captive portal for unconfigured info
    solisInfo = {}
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
    wlan.connect(solisInfo["wifiSSID"], solisInfo["wifiPass"])
    ipAddress, netMask, defaultGateway, DNS = wlan.ifconfig()
    wifiCount = 0
    while ipAddress == "0.0.0.0" and wifiCount < 30:
        print(".", end="")
        sleep(1)
        ipAddress, netMask, defaultGateway, DNS = wlan.ifconfig()
        wifiCount += 1

    if ipAddress == "0.0.0.0":
        print("No WiFi connection - please check details in solis.env")
        sys.exit()

    print("Wifi connected - IP address is: " + ipAddress)

    ntptime.host = "0.uk.pool.ntp.org"
    ntptime.settime()

    # Main loop
    # Get the solis data

    uasyncio.create_task(display_data(solisInfo, lcd))

    while True:
        await wait_button(btn)
        await display_solar_today(lcd)


if __name__ == "__main__":
    try:
        # Start event loop and run entry point coroutine
        uasyncio.run(main())
    except KeyboardInterrupt:
        pass
