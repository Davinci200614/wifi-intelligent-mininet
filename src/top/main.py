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
    info("\n*** Live-edit commands (graph updates immediately):\n"
         "    range   <node> <meters>        e.g. range ap1 400\n"
         "    move    <node> <x> <y> [z]     e.g. move sta1 450 300\n"
         "    txpower <node> <dBm>           e.g. txpower ap1 15\n"
         "    status                         positions, ranges, associations\n"
         "    refresh  (or just press Enter) repaint the graph window\n"
         "*** Other useful commands:\n"
         "    sta1 ping -c3 sta2             test connectivity\n"
         "    pingall                        ping every node\n"
         "    xterm sta1                     open a terminal on a node\n"
         "    exit                           stop the simulation\n\n")


# ==================== LIVE GRAPH HELPERS =============================
# Uses the matplotlib / mn_wifi.plot modules that Mininet-WiFi already
# loaded (via sys.modules), so no extra imports are needed.

def _plt():
    plt = sys.modules.get('matplotlib.pyplot')
    if plt is not None and plt.fignum_exists(1):
        return plt
    return None


def pump_graph():
    "Let the graph window process events so it repaints."
    plt = _plt()
    if plt is None:
        return
    try:
        plt.draw()
        plt.pause(0.001)
    except Exception:
        pass


def redraw_node(node):
    "Redraw one node's dot, label and range circle at its current values."
    plt = _plt()
    plot_mod = sys.modules.get('mn_wifi.plot')
    if plt is None or plot_mod is None:
        return
    p2d = plot_mod.Plot2D
    if p2d.ax is None:
        return
    try:
        if hasattr(node, 'circle') and hasattr(node, 'plt_node'):
            node.circle.set_radius(node.get_max_radius())
            node.update_2d()
        else:
            # Node was never drawn (e.g. AP missing its circle): draw it now
            p2d.instantiate_attrs(node)
    except Exception as e:
        info("*** graph: could not redraw %s (%s)\n" % (node.name, e))
    pump_graph()


class LiveCLI(CLI):
    "Mininet-WiFi CLI with commands that update the graph live."

    def _node(self, name):
        try:
            return self.mn[name]
        except KeyError:
            info("*** unknown node '%s'\n" % name)
            return None

    def do_range(self, line):
        "Change a node's range live.  Usage: range <node> <meters>"
        args = line.split()
        if len(args) != 2:
            info("usage: range <node> <meters>\n")
            return
        node = self._node(args[0])
        if node is None:
            return
        node.wintfs[0].setRange(float(args[1]))   # radio + links, no graph
        redraw_node(node)

    def do_txpower(self, line):
        "Change a node's tx power live.  Usage: txpower <node> <dBm>"
        args = line.split()
        if len(args) != 2:
            info("usage: txpower <node> <dBm>\n")
            return
        node = self._node(args[0])
        if node is None:
            return
        node.wintfs[0].setTxPower(int(args[1]))
        info("*** %s: tx power %s dBm -> range %.1fm\n"
             % (node.name, args[1], node.wintfs[0].range))
        redraw_node(node)

    def do_move(self, line):
        "Move a node live.  Usage: move <node> <x> <y> [z]"
        args = line.split()
        if len(args) not in (3, 4):
            info("usage: move <node> <x> <y> [z]\n")
            return
        node = self._node(args[0])
        if node is None:
            return
        z = args[3] if len(args) == 4 else '0'
        node.position = [float(args[1]), float(args[2]), float(z)]
        try:
            if getattr(node, 'wmIfaces', None):
                node.set_pos_wmediumd(node.position)
        except Exception:
            pass
        node.configLinks()                       # re-evaluate association
        redraw_node(node)

    def do_status(self, line):
        "Show position, range and association of every node."
        for node in self.mn.aps + self.mn.stations:
            intf = node.wintfs[0]
            pos = ','.join('%g' % v for v in node.position)
            assoc = ''
            if hasattr(intf, 'associatedTo') and intf.associatedTo:
                assoc = '  -> ' + intf.associatedTo.node.name
            info("    %-6s pos=%-14s range=%6.1fm  tx=%s dBm%s\n"
                 % (node.name, pos, intf.range, intf.txpower, assoc))

    def do_refresh(self, line):
        "Repaint the graph window."
        pump_graph()

    def postcmd(self, stop, line):
        # Repaint after every command (and on a bare Enter)
        pump_graph()
        return stop


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
    pump_graph()
    LiveCLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    custom_topology()