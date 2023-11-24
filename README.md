# solar-display-micropython
A version of the solar display using MicroPython

It uses the [Solis API](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-api-access-soliscloud) which allows users of Solis inverters to collect current and historical data

The intention is that it will show the main details on a 1602 display - I'm working on one with an i2c interface, using code from https://github.com/dhylands/python_lcd


## Note: ESP32 only
This currently doesn't work on a WeMos D1mini (and maybe other ESP8266 devices) because of this:
[github.com/micropython/micropython-lib/issues/400](https://github.com/micropython/micropython-lib/issues/400) 

## Hardware
I'm using a WEMOS LOLIN32 ESP32 LITE which has just about enough memory to do the job. 
My plan is to move to a WEMOS S2MINI because it's smaller.

## TODO
- async goodness - looks like it's working
- reset button  - use the EN pin to GND on a switch
- second button to display solar so far today  - in progress (pin 35)
- LCD brightness over i2c - https://forum.arduino.cc/t/lcd-2004-display-i2c-and-brightness/452720
  (might need a level converter since the GPIO is only 3.3v)