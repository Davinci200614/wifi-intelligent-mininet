#!/usr/bin/python

import sys
import os

# Add the local libs/mininet-wifi directory to Python's search path
local_mn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs', 'mininet-wifi'))
if local_mn_path not in sys.path:
    sys.path.insert(0, local_mn_path)

from mininet.node import Controller, OVSController
# Change controller=Controller to use RemoteController or UserSpaceController if needed
from mininet.log import setLogLevel, info
from mn_wifi.node import OVSKernelAP
from mn_wifi.net import Mininet_wifi
from mn_wifi.cli import CLI

def custom_topology():
    net = Mininet_wifi(controller=OVSController, accessPoint=OVSKernelAP)

    info("*** Adding controller\n")
    c0 = net.addController('c0')

    info("*** Adding access points and stations\n")
    ap1 = net.addAccessPoint('ap1', ssid='wifi-ssid-1', mode='g', channel='1', position='300,300,0')
    sta1 = net.addStation('sta1', ip='10.0.0.1', position='30,30,0')
    sta2 = net.addStation('sta2', ip='10.0.0.2', position='90,30,0')

    info("*** Configuring Wi-Fi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)

    # Enable the graphical visualizer window mapping coordinates
    net.plotGraph(max_x=1000, max_y=1000)

    info("*** Starting network\n")
    net.build()
    c0.start()
    ap1.start([c0])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    custom_topology()