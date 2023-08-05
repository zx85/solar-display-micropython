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
def connect_to_wifi(oled,env):
    wlan=network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting",end="")
    oled_text(oled,'Connecting',30,18,True)
    oled_text(oled,'to WiFi',40,38)
 
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
        oled_text(oled,'Wifi failed',0,7,True)
        oled_text(oled,'Please reset',0,30)
        oled_text(oled,'or check config',0,50)
        sys.exit()

    print("Wifi connected - IP address is: "+ipAddress)
    oled_text(oled,'Connected OK',0,7,True)
    oled_text(oled,'IP address: ',0,30)
    oled_text(oled,ipAddress,0,50)
    sleep(3)

def set_time(oled):
    count=3
    oled_text(oled,"NTP sync",20,28,True)

    while count>0 and count<99:
        try:
            ntptime.host="uk.pool.ntp.org"
            ntptime.settime()
            count=99
        except Exception as e:
            print ("ntptime didn't work: " + str(e))
            count-=1
            if count>=1:
                print ("retrying")
            sleep(5)
    if count==99:
        sleep(2)
        oled_text(oled,"Time sync OK",10,28,True)
        sleep(2)
    else:
        oled_text(oled,"Time sync fail",0,7,True)
        oled_text(oled,"Please reset",0,40)
        sys.exit()

def set_oled():
    # ESP32 Pin assignment 
    i2c = SoftI2C(scl=Pin(15), sda=Pin(14))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    return oled

def oled_text(oled,text,x,y,cls=False):
    if cls:
        oled.fill(0)
    oled.text(text,x,y)
    oled.show()

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
 
    resp_json={}
    try:
        gc.collect()
        resp = requests.post(req, data=Body, headers=header,timeout=60)
        gc.collect()
        print("["+str(resp.status_code)+"]")
        if resp.status_code==200:
            resp_json = resp.json()
    except Exception as e:
        print ("get solar_usage didn't work sorry because this: " + str(e))

# Try to make some sense of the results
    solar_usage={}
    if "data" in resp_json:
# Timestamp is text
        solar_usage['timestamp']=resp_json['data']['dataTimestamp']
# Battery is float
        solar_usage['batteryPer']=resp_json['data']['batteryCapacitySoc']
# Everything else has units
        if resp_json['data']['pac'] < 1:
            solar_usage['solarIn']=str(int(resp_json['data']['pac']*1000))+"W"
        else:
            solar_usage['solarIn']=str(resp_json['data']['pac'])[:4]+"kW"
        if abs(resp_json['data']['psum']) < 1:
             solar_usage['gridIn']=str(int(resp_json['data']['psum']*1000))+"W"
        else:
            solar_usage['gridIn']=str(resp_json['data']['psum'])[:4]+"kW"
        if resp_json['data']['familyLoadPower'] < 1:
            solar_usage['powerUsed']=str(int(resp_json['data']['familyLoadPower']*1000))+"W"
        else:
            solar_usage['powerUsed']=str(resp_json['data']['familyLoadPower'])[:4]+"kW"
        if resp_json['data']['eToday'] < 1:
            solar_usage['solarToday']=str(int(resp_json['data']['eToday']*1000))+"W"
        else:
            solar_usage['solarToday']=str(resp_json['data']['eToday'])[:4]+"kW"
    return solar_usage

def show_oled(oled,solar_usage,last):
    last_timestamp=last.split("|")[0]
    last_bat=float(last.split("|")[1])
    if last_timestamp!=solar_usage['timestamp']:
        oled_text(oled,'sol  '+solar_usage['solarIn'], 0, 5, True)
        oled_text(oled,'bat  '+str(int(solar_usage['batteryPer']))+'%', 0, 18)

        if last_bat<solar_usage['batteryPer']:
            oled_text(oled,'^',80,18)
        if last_bat==solar_usage['batteryPer']:
            oled_text(oled,'=',80,18)
        if last_bat>solar_usage['batteryPer']:
            oled_text(oled,'v',80,18)

        oled_text(oled,'grid '+solar_usage['gridIn'], 0, 30)
        oled_text(oled,'use  '+solar_usage['powerUsed'], 0, 42)
        sleep(1)
        oled_text(oled,'solDay '+solar_usage['solarToday'], 0, 54)
        last=solar_usage['timestamp']+"|"+str(solar_usage['batteryPer'])
    return last

def set_pixel(oled,pixel,status=1):
    if pixel=="updating":
        oled.pixel(127,0,status)
    if pixel=="recovering":
        oled.pixel(127,63,status)
    oled.show()

def main():

    oled=set_oled()

    env=get_env("config/solis.env")    
    connect_to_wifi(oled,env)
    set_time(oled)


    last="0|0"
    while True:
        set_pixel(oled,"updating")
        solar_usage=getSolis(env)
        if 'timestamp' in solar_usage:
# Clear the 'awaiting recovery' pixel
            set_pixel(oled,"recovering",0)
# And show the new value if there is one            
            last=show_oled(oled,solar_usage,last)
        else:
            print("No data returned")
            count=4
            while count>-1:
                set_pixel(oled,"updating",count%2)
                sleep(0.5)
                count-=1
# Show the 'awaiting recovery' pixel
            set_pixel(oled,"recovery")

# Then clear the 'updating' pixel
        set_pixel(oled,"updating",0)
        sleep(45)   
        
if __name__ == "__main__":
    main()
