# on-board goodies
import sys
import gc
import json
from hashlib import sha1
import urequests as requests
from time import sleep, gmtime
import network
import ntptime
from machine import Pin, SoftI2C
# external things
sys.path.append('/include')
import hmac
import base64
import md5
import ssd1306

# Local time doings
def stringTime(thisTime):
    Year,Month,Date,Hour,Minute,Second,Weekday,Yearday=thisTime  
    weekDay={0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
    monthName={1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    stringTime=weekDay[Weekday]+", "+f'{Date:02}'+" "+monthName[Month]+" "+f'{Year:02}'+" "+f'{Hour:02}'+":"+f'{Minute:02}'+":"+f'{Second:02}'+" GMT"
    return stringTime

# read the configuration file
def get_env(filename):
    env={}
    f = open(filename)
    for line in f:
        if "=" in line:
            thisAttr=(line.strip().split("=")[0])
            thisVal=(line.strip().split("=")[1])
            env[thisAttr]=thisVal
    f.close()
    return env

# connect to wifi bit. 
def connect_to_wifi(env):
    wlan=network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting",end="")
    wlan.connect(env['wifiSSID'],env['wifiPass'])
    ipAddress,netMask,defaultGateway,DNS=wlan.ifconfig()
    wifiCount=0
    while ipAddress=='0.0.0.0' and wifiCount<30:
        print(".",end="")
        sleep(1)
        ipAddress,netMask,defaultGateway,DNS=wlan.ifconfig()
        wifiCount+=1
    
    if ipAddress=="0.0.0.0":
        print("No WiFi connection - please check details in solis.env")
        sys.exit()

    print("Wifi connected - IP address is: "+ipAddress)

def set_time():
    ntptime.host="0.uk.pool.ntp.org"
    ntptime.settime()

def set_oled():
    # ESP32 Pin assignment 
    i2c = SoftI2C(scl=Pin(15), sda=Pin(14))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    return oled

def getSolis(env):
    url = env['solisUrl']
    CanonicalizedResource = env['solisPath']
    req = url + CanonicalizedResource
    VERB="POST"
    Content_Type = "application/json"

    Date=stringTime(gmtime())
    
    Body = '{"pageSize":100,  "id": "'+env['solisId']+'", "sn": "'+env['solisSn']+'" }'
    Content_MD5 = base64.b64encode(md5.digest(Body.encode('utf-8'))).decode('utf-8')
    encryptStr = (VERB + "\n"
        + Content_MD5 + "\n"
        + Content_Type + "\n"
        + Date + "\n"
        + CanonicalizedResource)
    h = hmac.new(env['solisSecret'].encode('utf-8'), msg=encryptStr.encode('utf-8'), digestmod=sha1)
    Sign = base64.b64encode(h.digest())
    Authorization = "API " + env['solisKey'] + ":" + Sign.decode('utf-8')
    
    header = { "Content-MD5":Content_MD5,
                "Content-Type":Content_Type,
                "Date":Date,
                "Authorization":Authorization
                }

    try:
        gc.collect()
        resp = requests.post(req, data=Body, headers=header,timeout=60)
        gc.collect()
        print("["+str(resp.status_code)+"]")
        resp_json={}
        if resp.status_code==200:
            resp_json = resp.json()
    except Exception as e:
        print ("get solar_usage didn't work sorry because this: " + str(e))

# Try to make some sense of the results
    solar_usage={}
    if "data" in resp_json:
        solar_usage['timestamp']=resp_json['data']['dataTimestamp']
        solar_usage['solarIn']=str(resp_json['data']['pac'])
        solar_usage['batteryPer']=str(resp_json['data']['batteryCapacitySoc'])
        solar_usage['gridIn']=str(resp_json['data']['psum'])
        solar_usage['powerUsed']=str(resp_json['data']['familyLoadPower'])
        solar_usage['solarToday']=str(resp_json['data']['eToday'])
    return solar_usage

def show_oled(oled,solar_usage):
    oled.fill(0)
    oled.text('sol  '+solar_usage['solarIn']+'kW', 0, 5)
    oled.text('bat  '+solar_usage['batteryPer']+'%', 0, 18)
    oled.text('grid '+solar_usage['gridIn']+'kW', 0, 30)
    oled.text('use  '+solar_usage['powerUsed']+'kW', 0, 42)
    oled.show()
    sleep(1.5)
    oled.text('solDay '+solar_usage['solarToday']+'kW', 0, 54)
    oled.show()

def main():

    env=get_env("config/solis.env")    
    connect_to_wifi(env)
    set_time()

    oled=set_oled()

    while True:

        solar_usage=getSolis(env)
        if 'timestamp' in solar_usage:
            show_oled(oled,solar_usage)
        else:
            print("No data returned")
        sleep(45)

        
if __name__ == "__main__":
    main()
