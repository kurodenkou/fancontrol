#!/usr/bin/python3
from pysnmp.hlapi import *
from time import sleep
import sqlite3
import subprocess


def ipmitool(args, host):
    global state

    cmd = ["ipmitool"]
    cmd += ['-I', 'lanplus']
    cmd += ['-H', host]
    cmd += ['-U', "root"] # Change as needed
    cmd += ['-P', "calvin"] # Change as needed
    cmd += (args.split(' '))

    try:
        subprocess.check_output(cmd, timeout=15)
    except subprocess.CalledProcessError:
        print("\"{}\" command has returned a non-0 exit code".format(cmd), file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("\"{}\" command has timed out".format(cmd), file=sys.stderr)
        return False
    return True


def record_data(conn, data):
    c = conn.cursor()
    c.execute('''INSERT INTO sensor_data (fan_speed, inlet_temp, outlet_temp, cpu1_temp, cpu2_temp)
                 VALUES (?, ?, ?, ?, ?)''', 
              (data['fan_speed'], float(data['inlet_temp'])/10, float(data['outlet_temp'])/10, float(data['cpu1_temp'])/10, float(data['cpu2_temp'])/10))
    conn.commit()


def query_idrac(host, community):
    oids = {
        'fan_speed': '.1.3.6.1.4.1.674.10892.5.4.700.12.1.6.1.1',
        'inlet_temp': '.1.3.6.1.4.1.674.10892.5.4.700.20.1.6.1.1',
        'outlet_temp': '.1.3.6.1.4.1.674.10892.5.4.700.20.1.6.1.2',
        'cpu1_temp': '.1.3.6.1.4.1.674.10892.5.4.700.20.1.6.1.3',
        'cpu2_temp': '.1.3.6.1.4.1.674.10892.5.4.700.20.1.6.1.4'
    }
    
    data = {}
    for key, oid in oids.items():
        iterator = getCmd(
                          SnmpEngine(),
                          CommunityData(community), # , mpModel=0),
                          UdpTransportTarget((host, 161)),
                          ContextData(),
                          ObjectType(ObjectIdentity(oid)))
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication:
            print(errorIndication)
            continue
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            continue
        else:
            for varBind in varBinds:
                data[key] = varBind[1].prettyPrint()
    return data


def adjust_fan_speed(host, community, current_data, previous_data):
    fan_speed_oid = '.1.3.6.1.4.1.674.10892.5.4.700.12.1.6.1.1'
    
    if current_data['cpu1_temp'] > str(50) or current_data['cpu2_temp'] > str(50):
        new_speed = 25
    elif current_data['cpu1_temp'] < str(40) and current_data['cpu2_temp'] < str(40):
        new_speed = 7
    else:
        if current_data['cpu1_temp'] > str(49) or current_data['cpu2_temp'] > str(49):
            new_speed = min(100, previous_data['fan_speed'] + 1)
        else:
            new_speed = max(0, previous_data['fan_speed'] - 1)
    return new_speed
    

# Initial Values
ip = ''
community = 'public'
# set the temps to near your threshold.  Fan speed too.  Fan speed is percent 0-100.
data = {'fan_speed': 23, 'cpu1_temp': 49, 'cpu2_temp': 49}
# Sets fan speed to manual.
ipmitool("raw 0x30 0x30 0x01 0x00", ip)

# Why a big while statement?  It works.
while True:
	# on first run it picks up above. On subsequent runs it uses actual previous data.
	previous_data = data
	data = query_idrac(ip, community)
	# Debugging
	fan_speed = "Fan Speed: "+data["fan_speed"]+" "
	inlet_temp = "Inlet Temp: "+str(float(data["inlet_temp"])/10)+" C "
	outlet_temp = "Outlet Temp: "+str(float(data["outlet_temp"])/10)+ " C "
	cpu1_temp = "CPU 1 Temp: "+str(float(data["cpu1_temp"])/10)+" C "
	cpu2_temp = "CPU 2 Temp: "+str(float(data["cpu2_temp"])/10)+" C "
	print(fan_speed+inlet_temp+outlet_temp+cpu1_temp+cpu2_temp)
	# Write to DB
	conn = sqlite3.connect('idrac_data.db')
	record_data(conn, data)
	conn.close()
	# get a new speed from the.. math.
	new_speed = adjust_fan_speed(ip, community, data, previous_data)
	data['fan_speed'] = new_speed
	# More debugging
	print("New Speed: "+ str(new_speed))
	# Actually set the new fan speed
	wanted_percentage_hex = "{0:#0{1}x}".format(new_speed, 4)
	ipmitool("raw 0x30 0x30 0x02 0xff {}".format(wanted_percentage_hex), ip)
	# Wait 5 seconds and do it again.
	sleep(5)
