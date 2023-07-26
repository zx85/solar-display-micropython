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

def getSolis(solisInfo):
    solar_usage={}

    url = solisInfo['solisUrl']
    CanonicalizedResource = solisInfo['solisPath']

    req = url + CanonicalizedResource
    VERB="POST"
    Content_Type = "application/json"

    Date=stringTime(gmtime())
    
    Body = '{"pageSize":100,  "id": "'+solisInfo['solisId']+'", "sn": "'+solisInfo['solisSn']+'" }'
    Content_MD5 = base64.b64encode(md5.digest(Body.encode('utf-8'))).decode('utf-8')
    encryptStr = (VERB + "\n"
        + Content_MD5 + "\n"
        + Content_Type + "\n"
        + Date + "\n"
        + CanonicalizedResource)
    h = hmac.new(solisInfo['solisSecret'].encode('utf-8'), msg=encryptStr.encode('utf-8'), digestmod=sha1)
    Sign = base64.b64encode(h.digest())
    Authorization = "API " + solisInfo['solisKey'] + ":" + Sign.decode('utf-8')
    
    header = { "Content-MD5":Content_MD5,
                "Content-Type":Content_Type,
                "Date":Date,
                "Authorization":Authorization
                }

    try:
        print("Memory free before gc: "+str(gc.mem_free()))
        gc.collect()
        print("Memory free after gc: "+ str(gc.mem_free()))
        print("\n\nPOST to "+url+"...",end="")
        resp = requests.post(req, data=Body, headers=header,timeout=60)
        print("["+str(resp.status_code)+"]")
        solar_usage = resp.json()
    except Exception as e:
        print ("get solar_usage didn't work sorry because this: " + str(e))

    return solar_usage

def main():

    solisInfo={}
    f = open('config/solis.env')
    for line in f:
        if "=" in line:
            thisAttr=(line.strip().split("=")[0])
            thisVal=(line.strip().split("=")[1])
            solisInfo[thisAttr]=thisVal
    f.close()
    wlan=network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Connecting",end="")
    wlan.connect(solisInfo['wifiSSID'],solisInfo['wifiPass'])
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

    ntptime.host="0.uk.pool.ntp.org"
    ntptime.settime()

    while True:

        solar_usage=getSolis(solisInfo)

        if "data" in solar_usage:
            timestamp=solar_usage['data']['dataTimestamp']
            solarIn=str(solar_usage['data']['pac'])
            batteryPer=str(solar_usage['data']['batteryCapacitySoc'])
            gridIn=str(solar_usage['data']['psum'])
            powerUsed=str(solar_usage['data']['familyLoadPower'])
            solarToday=str(solar_usage['data']['eToday'])
            print("solis timestamp is: "+timestamp)
            print("solarIn is: "+solarIn)
            print("batteryPer is: "+batteryPer)
            print("gridIn is: "+gridIn)
            print("powerUsed is: "+powerUsed)
            print("solarToday is: "+solarToday+"\n")
        else:
            print("No data returned")
        sleep(45)

        
if __name__ == "__main__":
    main()
