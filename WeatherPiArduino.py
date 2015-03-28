#!/usr/bin/env python
#
# WeatherPiArduino Test File
# Version 1.1 February 12, 2015
#
# SwitchDoc Labs
# www.switchdoc.com
#
#

# imports

import sys
import time
from datetime import datetime
import random 

import subprocess
import RPi.GPIO as GPIO

sys.path.append('./RTC_SDL_DS3231')
sys.path.append('./Adafruit_Python_BMP')
sys.path.append('./Adafruit_Python_GPIO')
sys.path.append('./SDL_Pi_Weather_80422')
sys.path.append('./SDL_Pi_FRAM')
sys.path.append('./RaspberryPi-AS3935/RPi_AS3935')


import SDL_DS3231
import Adafruit_BMP.BMP085 as BMP180
import SDL_Pi_Weather_80422 as SDL_Pi_Weather_80422

import SDL_Pi_FRAM
from RPi_AS3935 import RPi_AS3935

################

#WeatherRack Weather Sensors
#
# GPIO Numbering Mode GPIO.BCM
#

anenometerPin = 23
rainPin = 24

# constants

SDL_MODE_INTERNAL_AD = 0
SDL_MODE_I2C_ADS1015 = 1

#sample mode means return immediately.  THe wind speed is averaged at sampleTime or when you ask, whichever is longer
SDL_MODE_SAMPLE = 0
#Delay mode means to wait for sampleTime and the average after that time.
SDL_MODE_DELAY = 1

weatherStation = SDL_Pi_Weather_80422.SDL_Pi_Weather_80422(anenometerPin, rainPin, 0,0, SDL_MODE_I2C_ADS1015)

weatherStation.setWindMode(SDL_MODE_SAMPLE, 5.0)
#weatherStation.setWindMode(SDL_MODE_DELAY, 5.0)


################

# DS3231/AT24C32 Setup
filename = time.strftime("%Y-%m-%d%H:%M:%SRTCTest") + ".txt"
starttime = datetime.utcnow()

ds3231 = SDL_DS3231.SDL_DS3231(1, 0x68)
#comment out the next line after the clock has been initialized
ds3231.write_now()
################

# BMP180 Setup (compatible with BMP085)

bmp180 = BMP180.BMP085()

################

# ad3935 Set up Lightning Detector

as3935 = RPi_AS3935(address=0x03, bus=1)

as3935.set_indoors(True)
as3935.set_noise_floor(0)
as3935.calibrate(tun_cap=0x0F)

as3935LastInterrupt = 0
as3935LightningCount = 0
as3935LastDistance = 0
as3935LastStatus = ""

def handle_as3935_interrupt(channel):
    time.sleep(0.003)
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus
    reason = as3935.get_interrupt()
    as3935LastInterrupt = reason
    if reason == 0x01:
	as3935LastStatus = "Noise Floor too low. Adjusting"
        as3935.raise_noise_floor()
    elif reason == 0x04:
	as3935LastStatus = "Disturber detected - masking"
        as3935.set_mask_disturber(True)
    elif reason == 0x08:
        now = datetime.now().strftime('%H:%M:%S - %Y/%m/%d')
        distance = as3935.get_distance()
	as3935LastDistance = distance
	as3935LastStatus = "Lightning Detected "  + str(distance) + "km away. (%s)" % now



as3935pin = 25

GPIO.setup(as3935pin, GPIO.IN)
GPIO.add_event_detect(as3935pin, GPIO.RISING, callback=handle_as3935_interrupt)

###############

# Set up FRAM 

fram = SDL_Pi_FRAM.SDL_Pi_FRAM(addr = 0x50)

# Main Loop - sleeps 10 seconds
# Tests all I2C devices on WeatherPiArduino 


# Main Program

print ""
print "WeatherPiArduino Demo / Test Version 1.0 - SwitchDoc Labs"
print ""
print ""
print "Program Started at:"+ time.strftime("%Y-%m-%d %H:%M:%S")
print ""

totalRain = 0

while True:




	print "---------------------------------------- "
	print "----------------- "
	print " WeatherRack Weather Sensors" 
	print "----------------- "
	#

 	currentWindSpeed = weatherStation.current_wind_speed()/1.6
  	currentWindGust = weatherStation.get_wind_gust()/1.6
  	totalRain = totalRain + weatherStation.get_current_rain_total()/25.4
  	print("Rain Total=\t%0.2f in")%(totalRain)
  	print("Wind Speed=\t%0.2f MPH")%(currentWindSpeed)
    	print("MPH wind_gust=\t%0.2f MPH")%(currentWindGust)
  	
	print "Wind Direction=\t\t\t %0.2f Degrees" % weatherStation.current_wind_direction()
	print "Wind Direction Voltage=\t\t %0.3f V" % weatherStation.current_wind_direction_voltage()

	print "----------------- "
	print "----------------- "
	print " DS3231 Real Time Clock"
	print "----------------- "
	#
	currenttime = datetime.utcnow()

	deltatime = currenttime - starttime
 
	print "Raspberry Pi=\t" + time.strftime("%Y-%m-%d %H:%M:%S")
	
	print "DS3231=\t\t%s" % ds3231.read_datetime()

	print "DS3231 Temperature= \t%0.2f C" % ds3231.getTemp()
	# do the AT24C32 eeprom

	print "----------------- "
	print "----------------- "
	print " AT24C32 EEPROM"
	print "----------------- "
	print "writing first 4 addresses with random data"
	for x in range(0,4):
		value = random.randint(0,255)
		print "address = %i writing value=%i" % (x, value) 	
		ds3231.write_AT24C32_byte(x, value)
	print "----------------- "

	print "reading first 4 addresses"
	for x in range(0,4):
		print "address = %i value = %i" %(x, ds3231.read_AT24C32_byte(x)) 
	print "----------------- "
	print "----------------- "
	print " BMP180 Barometer/Temp/Altitude"
	print "----------------- "

	print 'Temperature = \t{0:0.2f} C'.format(bmp180.read_temperature())
	print 'Pressure = \t{0:0.2f} KPa'.format(bmp180.read_pressure()/1000)
	print 'Altitude = \t{0:0.2f} m'.format(bmp180.read_altitude())
	print 'Sealevel Pressure = \t{0:0.2f} KPa'.format(bmp180.read_sealevel_pressure()/1000)
	print "----------------- "

	print "----------------- "
	print " HTU21DF Humidity and Temperature"
	print "----------------- "

	# We use a C library for this device as it just doesn't play well with Python and smbus/I2C libraries

	HTU21DFOut = subprocess.check_output(["htu21dflib/htu21dflib","-l"])
	splitstring = HTU21DFOut.split()

	HTUtemperature = float(splitstring[0])	
	HTUhumidity = float(splitstring[1])	
	print "Temperature = \t%0.2f C" % HTUtemperature
	print "Humidity = \t%0.2f %%" % HTUhumidity
	print "----------------- "

	print "----------------- "
	print " AS3853 Lightning Detector "
	print "----------------- "

	print "Last result from AS3953:"

	if (as3935LastInterrupt == 0x00):
		print "----No Lightning detected---"
		
	if (as3935LastInterrupt == 0x01):
		print "Noise Floor: %s" % as3935LastStatus
		as3935LastInterrupt = 0x00

	if (as3935LastInterrupt == 0x04):
		print "Disturber: %s" % as3935LastStatus
		as3935LastInterrupt = 0x00

	if (as3935LastInterrupt == 0x08):
		print "Lightning: %s" % as3935LastStatus
		as3935LightningCount += 1
		as3935LastInterrupt = 0x00

	print "Lightning Count = ", as3935LightningCount
	print "----------------- "
	
	print "----------------- "
	print " FRAM Byte Read Test "
	print "----------------- "

        print "writing first 3 addresses with random data"
        for x in range(0,3):
                value = random.randint(0,255)
                print "address = %i writing value=%i" % (x, value)
                fram.write8(x, value)
        print "----------------- "

        print "reading first 3 addresses"
        for x in range(0,3):
                print "address = %i value = %i" %(x, fram.read8(x))
        print "----------------- "
        print "----------------- "
	print



	time.sleep(10.0)

