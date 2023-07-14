import os
import json
import hashlib
from hashlib import sha1
import hmac
import base64
import urequests as requests
import time
import ntptime
from md5 import md5 

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

    Date=stringTime(time.gmtime())
    
    # Here's the bit where we get data from Solis
    Body = '{"pageSize":100,  "id": "'+solisInfo['solisId']+'", "sn": "'+solisInfo['solisSn']+'" }'
    Content_MD5 = base64.b64encode(hashlib.md5(Body.encode('utf-8')).digest()).decode('utf-8')
    encryptStr = (VERB + "\n"
        + Content_MD5 + "\n"
        + Content_Type + "\n"
        + Date + "\n"
        + CanonicalizedResource)
    h = hmac.new(solisInfo['solisSecret'], msg=encryptStr.encode('utf-8'), digestmod=hashlib.sha1)
    Sign = base64.b64encode(h.digest())
    Authorization = "API " + solisInfo['solisKey'] + ":" + Sign.decode('utf-8')
    
    header = { "Content-MD5":Content_MD5,
                "Content-Type":Content_Type,
                "Date":Date,
                "Authorization":Authorization
                }

    # Make the call
    try:
        resp = requests.post(req, data=Body, headers=header,timeout=60)
        print("response code: "+str(resp.status_code))
        solar_usage = resp.json()
    except Exception as e:
        print ("get solar_usage didn't work sorry because this: " + str(e))

    return solar_usage

# Doing stuff for the local file

def main():

    ntptime.host="0.uk.pool.ntp.org"
    ntptime.settime()

# solis info - from solis.env
    solisInfo={}
    f = open('solis.env')
    for line in f:
        if "=" in line:
            thisAttr=(line.strip().split("=")[0])
            thisVal=(line.strip().split("=")[1])
            solisInfo[thisAttr]=thisVal

    solar_usage=getSolis(solisInfo)

# solarIn: pac, 
# batteryPer: batteryCapacitySoc, 
# gridIn: psum, 
# powerUsed: familyLoadPower, 
# timestamp: dataTimestamp, 

    print("solis timestamp is: "+solar_usage['dataTimestamp'])
    print("solarIn is"+solar_usage['pac'])
    print("batteryPer is"+solar_usage['batteryCapacitySoc'])
    print("gridIn is"+solar_usage['psum'])
    print("powerUsed is"+solar_usage['powerUsed'])

if __name__ == "__main__":
    main()
