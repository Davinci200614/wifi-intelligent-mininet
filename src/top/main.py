#!/usr/bin/env python3
"""
Simple Mininet-WiFi test: 1 controller (c0), 1 access point (ap1), 1 station (sta1).
A wired host (h1) is plugged into ap1 so sta1 has something to ping.

Run:  sudo python3 wifi_test.py
GUI needs matplotlib:  sudo apt install python3-matplotlib
"""
import shutil
import time

# --- GUI fix: newer matplotlib (>= 3.6) removed canvas.set_window_title(),
# which older Mininet-WiFi still calls -> "Something went wrong with the GUI".
# Put the method back so the plot works with any matplotlib version.
try:
    from matplotlib.backend_bases import FigureCanvasBase
    if not hasattr(FigureCanvasBase, 'set_window_title'):
        def _set_window_title(self, title):
            if getattr(self, 'manager', None):
                self.manager.set_window_title(title)
        FigureCanvasBase.set_window_title = _set_window_title
except ImportError:
    pass

from mininet.log import setLogLevel, info
from mininet.node import Controller, OVSController, RemoteController
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP
from mn_wifi.cli import CLI


def add_controller(net):
    """Pick a controller that actually exists on this machine (avoids the PATH error)."""
    if shutil.which('controller'):
        info('*** Using reference controller\n')
        return net.addController('c0', controller=Controller)
    if shutil.which('ovs-testcontroller'):
        info('*** Using ovs-testcontroller\n')
        return net.addController('c0', controller=OVSController)
    info('*** No local controller found -> using remote controller at 127.0.0.1:6653\n'
         '    (start POX/Ryu first, e.g. "ryu-manager ryu.app.simple_switch_13")\n')
    return net.addController('c0', controller=RemoteController,
                             ip='127.0.0.1', port=6653)


def topology():
    net = Mininet_wifi(accessPoint=OVSKernelAP)

    info('*** Creating nodes\n')
    c0 = add_controller(net)
    ap1 = net.addAccessPoint('ap1', ssid='test-ssid', mode='g', channel='1',
                             position='50,50,0', range=30)
    sta1 = net.addStation('sta1', ip='10.0.0.1/8', position='40,50,0')
    h1 = net.addHost('h1', ip='10.0.0.2/8')

    info('*** Configuring WiFi nodes\n')
    net.configureNodes() if hasattr(net, 'configureNodes') else net.configureWifiNodes()

    info('*** Creating links\n')
    net.addLink(sta1, ap1)   # associate sta1 with ap1 explicitly
    net.addLink(ap1, h1)

    info('*** Opening GUI (live map of ap1 range and sta1 position)\n')
    net.plotGraph(max_x=100, max_y=100)

    info('*** Starting network\n')
    net.build()
    c0.start()
    ap1.start([c0])

    info('*** Waiting for sta1 to associate...\n')
    time.sleep(3)
    info(sta1.cmd('iw dev sta1-wlan0 link'))

    info('*** Testing connectivity (sta1 <-> h1)\n')
    net.pingAll()

    info('*** Running CLI (try: sta1 iw dev sta1-wlan0 link, sta1 ping h1)\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()