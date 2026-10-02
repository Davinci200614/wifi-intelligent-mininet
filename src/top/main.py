#!/usr/bin/python

import sys
import os

# Add the local libs/mininet-wifi directory to Python's search path
local_mn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs', 'mininet-wifi'))
if local_mn_path not in sys.path:
    sys.path.insert(0, local_mn_path)

from mininet.log import setLogLevel, info
from mn_wifi.node import OVSKernelAP
from mn_wifi.net import Mininet_wifi
from mn_wifi.cli import CLI

# ==================== CONFIGURATION VARIABLES ====================
AP_SSID = 'wifi-ssid-1'
AP_MODE = 'g'
AP_CHANNEL = '1'
AP_POSITION = '300,300,0'
AP_RANGE = 150

STA1_IP = '10.0.0.1'
STA1_POSITION = '30,30,0'

STA2_IP = '10.0.0.2'
STA2_POSITION = '90,30,0'

CANVAS_MAX_X = 1000
CANVAS_MAX_Y = 1000
# =================================================================

def custom_topology():
    net = Mininet_wifi(accessPoint=OVSKernelAP)

    info("*** Adding access points and stations\n")
    ap1 = net.addAccessPoint(
        'ap1', 
        ssid=AP_SSID, 
        mode=AP_MODE, 
        channel=AP_CHANNEL, 
        position=AP_POSITION, 
        range=AP_RANGE
    )
    sta1 = net.addStation('sta1', ip=STA1_IP, position=STA1_POSITION)
    sta2 = net.addStation('sta2', ip=STA2_IP, position=STA2_POSITION)

    info("*** Configuring Wi-Fi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    # Enable the graphical visualizer window mapping coordinates
    net.plotGraph(max_x=CANVAS_MAX_X, max_y=CANVAS_MAX_Y)

    info("*** Starting network\n")
    net.build()
    ap1.start([])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    custom_topology()