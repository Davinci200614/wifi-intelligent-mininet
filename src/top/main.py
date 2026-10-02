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

# =====================================================================
#                 EDIT THE SIMULATION HERE
# =====================================================================
# Add / remove / change entries in the lists below. Nothing else in the
# file needs to be touched.

# ---- Access points --------------------------------------------------
# No controller is used: failMode 'standalone' makes each AP behave as
# a normal learning switch so stations can talk to each other.
ACCESS_POINTS = [
    {
        'name': 'ap1',
        'ssid': 'wifi-ssid-1',
        'mode': 'g',            # a, b, g, n, ac
        'channel': '1',
        'position': '300,300,0',
        'range': 300,
    },
    # Uncomment to add a second AP:
    # {
    #     'name': 'ap2',
    #     'ssid': 'wifi-ssid-2',
    #     'mode': 'g',
    #     'channel': '6',
    #     'position': '700,300,0',
    #     'range': 300,
    # },
]

# ---- Stations -------------------------------------------------------
# 'ap'      : AP to link to at start (None = let signal strength decide)
# 'mobility': optional movement {'start': (t, 'x,y,z'), 'stop': (t, 'x,y,z')}
#             A station with mobility is NOT hard-linked to an AP, so it can
#             roam between APs as it moves.
STATIONS = [
    {
        'name': 'sta1',
        'ip': '10.0.0.1/8',
        'position': '150,150,0',
        'ap': 'ap1',
    },
    {
        'name': 'sta2',
        'ip': '10.0.0.2/8',
        'position': '250,150,0',
        'ap': 'ap1',
    },
    # Example of a moving station:
    # {
    #     'name': 'sta3',
    #     'ip': '10.0.0.3/8',
    #     'position': '100,300,0',
    #     'ap': None,
    #     'mobility': {
    #         'start': (1,  '100,300,0'),
    #         'stop':  (30, '800,300,0'),
    #     },
    # },
]

# ---- Radio propagation ---------------------------------------------
# Set to None to use the default model.
PROPAGATION_MODEL = {'model': 'logDistance', 'exp': 4}

# ---- Mobility timeline ---------------------------------------------
MOBILITY_START_TIME = 0
MOBILITY_STOP_TIME = 60

# ---- Graph window ---------------------------------------------------
SHOW_GRAPH = True
CANVAS_MAX_X = 1000
CANVAS_MAX_Y = 1000
# =====================================================================


def build_aps(net):
    aps = {}
    for cfg in ACCESS_POINTS:
        params = dict(cfg)
        name = params.pop('name')
        params.setdefault('failMode', 'standalone')   # no controller
        aps[name] = net.addAccessPoint(name, **params)
        info("    + %s  ssid=%s ch=%s pos=%s\n"
             % (name, cfg['ssid'], cfg['channel'], cfg['position']))
    return aps


def build_stations(net):
    stas = {}
    for cfg in STATIONS:
        stas[cfg['name']] = net.addStation(
            cfg['name'], ip=cfg['ip'], position=cfg['position'])
        info("    + %s  ip=%s pos=%s\n"
             % (cfg['name'], cfg['ip'], cfg['position']))
    return stas


def build_links(net, aps, stas):
    for cfg in STATIONS:
        ap_name = cfg.get('ap')
        if ap_name and not cfg.get('mobility'):
            if ap_name not in aps:
                raise ValueError("%s links to unknown AP '%s'"
                                 % (cfg['name'], ap_name))
            net.addLink(stas[cfg['name']], aps[ap_name])
            info("    %s <-> %s\n" % (cfg['name'], ap_name))


def build_mobility(net, stas):
    movers = [c for c in STATIONS if c.get('mobility')]
    if not movers:
        return
    info("*** Configuring mobility\n")
    net.startMobility(time=MOBILITY_START_TIME)
    for cfg in movers:
        start_t, start_pos = cfg['mobility']['start']
        stop_t, stop_pos = cfg['mobility']['stop']
        net.mobility(stas[cfg['name']], 'start', time=start_t, position=start_pos)
        net.mobility(stas[cfg['name']], 'stop', time=stop_t, position=stop_pos)
        info("    %s: %s (t=%s) -> %s (t=%s)\n"
             % (cfg['name'], start_pos, start_t, stop_pos, stop_t))
    net.stopMobility(time=MOBILITY_STOP_TIME)


def print_help():
    info("\n*** Useful CLI commands:\n"
         "    sta1 ping -c3 sta2                     test connectivity\n"
         "    pingall                                ping every node\n"
         "    sta1 iw dev sta1-wlan0 link            show association / signal\n"
         "    py sta1.setPosition('400,300,0')       move a station live\n"
         "    py ap1.setRange(150)                   change AP range live\n"
         "    py sta1.wintfs[0].rssi                 read station RSSI\n"
         "    exit                                   stop the simulation\n\n")


def custom_topology():
    net = Mininet_wifi(accessPoint=OVSKernelAP)

    info("*** Adding access points\n")
    aps = build_aps(net)

    info("*** Adding stations\n")
    stas = build_stations(net)

    if PROPAGATION_MODEL:
        net.setPropagationModel(**PROPAGATION_MODEL)

    info("*** Configuring Wi-Fi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    build_links(net, aps, stas)

    # Enable the graphical visualizer window mapping coordinates
    if SHOW_GRAPH:
        net.plotGraph(max_x=CANVAS_MAX_X, max_y=CANVAS_MAX_Y)

    build_mobility(net, stas)

    info("*** Starting network\n")
    net.build()
    for ap in aps.values():
        ap.start([])          # empty list = no controller

    print_help()
    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    custom_topology()
