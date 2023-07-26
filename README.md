# solar-display-micropython
A version of the solar display using MicroPython

It uses the [Solis API](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-api-access-soliscloud) which allows users of Solis inverters to collect current and historical data

The intention is that it will show the main details on a 1602 display - currently it's configured for a 4 pin GPIO connection.

Optional extra branch bit has support for ssd1306 for reasons.

## Note:
This currently doesn't work on a WeMos D1mini (and maybe other ESP8266 devices) because of this:
[github.com/micropython/micropython-lib/issues/400](https://github.com/micropython/micropython-lib/issues/400) 

It's been tested on a WeMos Lolin ESP32 Lite and an ESP32CAM

## TODO
Still need to do the display bit because I don't have a spare display...