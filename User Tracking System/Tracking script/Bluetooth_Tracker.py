import paho.mqtt.client as mqtt
import fcntl
import struct
import array
import bluetooth
import bluetooth._bluetooth as bt
import time
import json
import signal
import sys

def signal_handler(sig, frame):
    print("Disconnecting MQTT")
    client.loop_stop()
    client.disconnect()
    raise SystemExit

def on_connect(client, userdata, flags, rc):
    print("Connected with result code %s" % rc)

def guests_nearby(time):
    guests = bluetooth.discover_devices(duration=time)
    print(guests)
    for guest in guests:
        if(bluetooth_rssi(guest) > -15):
            return True
    return False

def bluetooth_rssi(addr):
    # Open hci socket
    hci_sock = bt.hci_open_dev()
    hci_fd = hci_sock.fileno()

    # Connect to device (to whatever you like)
    bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    bt_sock.settimeout(5)
    #
    
    try:
        #Get result
        result = bt_sock.connect((addr, 1))	# PSM 1 - Service Discovery

        # Get ConnInfo
        #Construct request to bit value
        reqstr = struct.pack("6sB17s", bt.str2ba(addr), bt.ACL_LINK, "\0" * 17)
        #request into array
        request = array.array("c", reqstr )
        #hamdler creation
        handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
        #unback request to handler
        handle = struct.unpack("8xH14x", request.tostring())[0]

        # Get RSSI
        #Handler into command body
        cmd_pkt=struct.pack('H', handle)

        #recive request
        result = bt.hci_send_req(
                                hci_sock,
                                bt.OGF_STATUS_PARAM,
                                bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 
                                4, 
                                cmd_pkt
                                )
        #get rssi to 
        rssi = struct.unpack('b', result[3])[0]

    # Close sockets
        bt_sock.close()
        hci_sock.close()

        return rssi

    except:
        #print("Error")
        return None


#MQTT setup
broker_address="192.168.1.217" 

#create new instance
client = mqtt.Client(client_id="P1", clean_session=False)
client.on_connect = on_connect
#connect to broker
client.connect(broker_address, port=1883)
client.loop_start()

#topic
topic = "rpi1/enrih"

#House users
enrih = "04:B4:29:08:8C:82"
margo = "04:B4:29:5B:CF:6C"
merilin = "88:E9:FE:A3:C6:2B"
anneli = "3C:2E:FF:B8:BC:67"
helena = "70:1F:3C:E7:32:A0"

#Room
room = "enrih"

#Print info out
debug = False

#Look for guests
lookup_guests = True

#Handle CTRL+Z
signal.signal(signal.SIGTSTP, signal_handler)
try:
    while True:

        #Guest present? Default = False
        guests = False

        #Look for guests if enabled
        if lookup_guests:
            guests = guests_nearby(5)

        # Get all home devices rssi values
        enrih_rssi = str(bluetooth_rssi(enrih))
        margo_rssi = str(bluetooth_rssi(margo))
        merilin_rssi = str(bluetooth_rssi(merilin))
        anneli_rssi = str(bluetooth_rssi(anneli))
        helena_rssi = str(bluetooth_rssi(helena))
        
        room_info = {
            "room": room,
            "guests": guests,
            "values": [
                {
                "enrih": enrih_rssi,
                "merilin": merilin_rssi,
                "helena": helena_rssi,
                "anneli": anneli_rssi,
                "margo": margo_rssi
                }
            ]
        }

        string_packet = json.dumps(room_info, separators=(',', ':'))

        client.publish(topic, string_packet)
        time.sleep(10)

        if(debug):
            print(string_packet)
            print("-----------")
            print(room_info)

except KeyboardInterrupt:
    pass
finally:
    print("End")
    client.loop_stop()
    client.disconnect()

