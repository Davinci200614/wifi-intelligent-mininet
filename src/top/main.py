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
ACCESS_POINTS = [
    {
        'name': 'ap1',
        'ssid': 'wifi-ssid-1',
        'mode': 'g',            # a, b, g, n, ac
        'channel': '1',
        'position': '300,300,0',
        'range': 300,
    },
    # {
    #     'name': 'ap2',
    #     'ssid': 'wifi-ssid-2',
    #     'mode': 'g',
    #     'channel': '6',
    #     'position': '700,300,0',
    #     'range': 300,
    # },
]

# 'ap'      : AP to link to at start (None = let signal strength decide)
# 'mobility': optional {'start': (t, 'x,y,z'), 'stop': (t, 'x,y,z')}
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
]

PROPAGATION_MODEL = {'model': 'logDistance', 'exp': 4}   # or None

MOBILITY_START_TIME = 0
MOBILITY_STOP_TIME = 60

SHOW_GRAPH = True
CANVAS_MAX_X = 1000
CANVAS_MAX_Y = 1000

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# =====================================================================


# Standard-library modules taken from what is already loaded, so the
# import block above stays unchanged.
def _lib(name):
    return sys.modules.get(name) or __import__(name)


# ==================== GRAPH FIX (newer matplotlib) ====================
# Mininet-WiFi calls plt_node.set_data(x, y) with single numbers. Newer
# matplotlib needs sequences ("x must be a sequence"), which breaks the
# initial drawing (circles stuck at 0,0) and every later update.

def patch_graph():
    node_mod = sys.modules.get('mn_wifi.node')
    plot_mod = sys.modules.get('mn_wifi.plot')

    def update_2d(self):
        x, y, z = self.getxyz()
        self.set_text_pos(x, y)
        self.plt_node.set_data([x], [y])
        self.circle.center = (x, y)
        self.updateLine()

    def plot_graph(self, nodes, links, **kwargs):
        for node in nodes:
            self.instantiate_attrs(node)    # uses the fixed update_2d
        self.create_line(links)

    # Patch every class that defines its own update_2d / plot_graph
    for mod, attr, fn in ((node_mod, 'update_2d', update_2d),
                          (plot_mod, 'plot_graph', plot_graph)):
        if mod is None:
            continue
        for obj in list(vars(mod).values()):
            if isinstance(obj, type) and attr in vars(obj) \
                    and getattr(obj, '__module__', '') == mod.__name__:
                setattr(obj, attr, fn)


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


def redraw_node(node, pump=True):
    "Redraw one node's dot, label and range circle at its current values."
    plot_mod = sys.modules.get('mn_wifi.plot')
    if _plt() is None or plot_mod is None or plot_mod.Plot2D.ax is None:
        return
    try:
        if not (hasattr(node, 'circle') and hasattr(node, 'plt_node')
                and hasattr(node, 'plttxt')):
            plot_mod.Plot2D.instantiate_annotate(node)
            plot_mod.Plot2D.instantiate_circle(node)
            plot_mod.Plot2D.instantiate_node(node)
        # Draw directly (does not depend on the library's update_2d)
        x = round(float(node.position[0]), 2)
        y = round(float(node.position[1]), 2)
        node.plttxt.xyann = (x, y)
        node.plt_node.set_data([x], [y])
        node.circle.center = (x, y)
        node.circle.set_radius(node.get_max_radius())
        try:
            node.updateLine()
        except Exception:
            pass
    except Exception as e:
        info("*** graph: could not redraw %s (%s)\n" % (node.name, e))
    if pump:
        pump_graph()


# ==================== BUILD HELPERS ===================================

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
    net.stopMobility(time=MOBILITY_STOP_TIME)


# ==================== MEASUREMENT HELPERS =============================

def sta_sample(net, sta):
    "One measurement for a station (pure Python, safe from any thread)."
    intf = sta.wintfs[0]
    ap_intf = getattr(intf, 'associatedTo', None)
    ap = ap_intf.node if ap_intf else None
    if ap is None and net.aps:                      # report nearest AP
        ap = min(net.aps, key=lambda a: sta.get_distance_to(a))
    dist = sta.get_distance_to(ap) if ap else 0.0
    return {
        'sta': sta.name,
        'x': round(float(sta.position[0]), 2),
        'y': round(float(sta.position[1]), 2),
        'ap': ap.name if ap else '-',
        'associated': 'yes' if ap_intf else 'no',
        'distance_m': round(dist, 2),
        'rssi_dbm': getattr(intf, 'rssi', 0),
        'ap_range_m': round(float(ap.wintfs[0].range), 1) if ap else 0,
        'ap_txpower_dbm': ap.wintfs[0].txpower if ap else 0,
    }


FIELDS = ['time_s', 'sta', 'x', 'y', 'ap', 'associated', 'distance_m',
          'rssi_dbm', 'ap_range_m', 'ap_txpower_dbm']


def print_samples(samples):
    info("    %-6s %-16s %-5s %-5s %9s %9s\n"
         % ('sta', 'position', 'ap', 'assoc', 'dist(m)', 'rssi(dBm)'))
    for s in samples:
        info("    %-6s %-16s %-5s %-5s %9.1f %9s\n"
             % (s['sta'], '%g,%g' % (s['x'], s['y']), s['ap'],
                s['associated'], s['distance_m'], s['rssi_dbm']))


def ping_once(src, dst_ip, count=1):
    "Return (loss_percent, avg_rtt_ms or None) from a short ping."
    out = src.cmd('ping -c %d -W 1 %s' % (count, dst_ip))
    loss, rtt = 100.0, None
    for line in out.splitlines():
        if 'packet loss' in line:
            for part in line.split(','):
                if 'packet loss' in part:
                    loss = float(part.strip().split('%')[0])
        if line.startswith('rtt') or line.startswith('round-trip'):
            rtt = float(line.split('=')[1].split('/')[1])
    return loss, rtt


def open_csv(filename, header):
    if not os.path.isabs(filename):
        if not os.path.isdir(DATA_DIR):
            os.makedirs(DATA_DIR)
        filename = os.path.join(DATA_DIR, filename)
    f = open(filename, 'w')
    f.write(','.join(header) + '\n')
    return f, filename


class Logger(object):
    "Background CSV logger of station measurements."

    def __init__(self, net, filename, interval, stas):
        self.net, self.interval, self.stas = net, interval, stas
        self.f, self.path = open_csv(filename, FIELDS)
        self.running = True
        self.t0 = _lib('time').time()
        self.thread = _lib('threading').Thread(target=self.loop)
        self.thread.daemon = True
        self.thread.start()

    def loop(self):
        time = _lib('time')
        while self.running:
            t = round(time.time() - self.t0, 2)
            for sta in self.stas:
                s = sta_sample(self.net, sta)
                s['time_s'] = t
                self.f.write(','.join(str(s[k]) for k in FIELDS) + '\n')
            self.f.flush()
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        self.thread.join(self.interval + 1)
        self.f.close()


# ==================== LIVE CLI ========================================

class LiveCLI(CLI):
    "Mininet-WiFi CLI with live-edit and data-collection commands."

    logger = None

    def _node(self, name):
        try:
            return self.mn[name]
        except KeyError:
            info("*** unknown node '%s'\n" % name)
            return None

    def _stations(self, line):
        names = line.split()
        if not names:
            return list(self.mn.stations)
        return [n for n in (self._node(x) for x in names) if n is not None]

    def _reassociate(self):
        "Re-evaluate every station's link (after a move / range change)."
        for sta in self.mn.stations:
            try:
                sta.configLinks()
            except Exception:
                pass

    # ---------- live edit ----------
    def do_range(self, line):
        "Change a node's range.  Usage: range <node> <meters>"
        args = line.split()
        if len(args) != 2:
            info("usage: range <node> <meters>\n")
            return
        node = self._node(args[0])
        if node is None:
            return
        node.wintfs[0].setRange(float(args[1]))
        self._reassociate()
        redraw_node(node)

    def do_txpower(self, line):
        "Change a node's tx power.  Usage: txpower <node> <dBm>"
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
        self._reassociate()
        redraw_node(node)

    def do_move(self, line):
        "Move a station or AP.  Usage: move <node> <x> <y> [z]"
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
        self._reassociate()
        redraw_node(node)

    # ---------- data ----------
    def do_rssi(self, line):
        "Show RSSI / distance / AP for stations.  Usage: rssi [sta ...]"
        print_samples([sta_sample(self.mn, s) for s in self._stations(line)])

    def do_watch(self, line):
        "Print RSSI repeatedly.  Usage: watch <seconds> [interval] [sta ...]"
        args = line.split()
        if not args:
            info("usage: watch <seconds> [interval] [sta ...]\n")
            return
        duration = float(args[0])
        interval = float(args[1]) if len(args) > 1 else 1.0
        stas = self._stations(' '.join(args[2:]))
        time = _lib('time')
        end = time.time() + duration
        try:
            while time.time() < end:
                info("--- t=%.1fs\n" % (duration - (end - time.time())))
                print_samples([sta_sample(self.mn, s) for s in stas])
                for n in self.mn.stations:
                    redraw_node(n, pump=False)
                pump_graph()
                time.sleep(interval)
        except KeyboardInterrupt:
            info("\n")

    def do_log(self, line):
        """Log measurements to CSV in the background.
           Usage: log start <file.csv> [interval] [sta ...] | log stop"""
        args = line.split()
        if args[:1] == ['stop']:
            if LiveCLI.logger:
                LiveCLI.logger.stop()
                info("*** logging stopped: %s\n" % LiveCLI.logger.path)
                LiveCLI.logger = None
            else:
                info("*** not logging\n")
            return
        if len(args) < 2 or args[0] != 'start':
            info("usage: log start <file.csv> [interval] [sta ...] | log stop\n")
            return
        if LiveCLI.logger:
            info("*** already logging to %s (log stop first)\n"
                 % LiveCLI.logger.path)
            return
        interval = float(args[2]) if len(args) > 2 else 1.0
        stas = self._stations(' '.join(args[3:]))
        LiveCLI.logger = Logger(self.mn, args[1], interval, stas)
        info("*** logging %s every %ss -> %s\n"
             % (','.join(s.name for s in stas), interval,
                LiveCLI.logger.path))

    def do_survey(self, line):
        """Walk a station along a line, recording RSSI (and ping) per step.
           Usage: survey <sta> <x1> <y1> <x2> <y2> <steps> [file.csv] [ping_target]"""
        args = line.split()
        if len(args) < 6:
            info("usage: survey <sta> <x1> <y1> <x2> <y2> <steps> "
                 "[file.csv] [ping_target]\n")
            return
        sta = self._node(args[0])
        if sta is None:
            return
        x1, y1, x2, y2 = [float(v) for v in args[1:5]]
        steps = max(1, int(args[5]))
        fname = args[6] if len(args) > 6 else 'survey_%s.csv' % sta.name
        target = self._node(args[7]) if len(args) > 7 else None
        header = FIELDS[1:] + ['ping_loss_pct', 'ping_rtt_ms']
        f, path = open_csv(fname, header)
        try:
            for i in range(steps + 1):
                x = x1 + (x2 - x1) * i / steps
                y = y1 + (y2 - y1) * i / steps
                self.do_move('%s %s %s' % (sta.name, x, y))
                s = sta_sample(self.mn, sta)
                loss, rtt = ('', '')
                if target is not None:
                    loss, rtt = ping_once(sta, target.IP())
                    rtt = '' if rtt is None else rtt
                s['ping_loss_pct'], s['ping_rtt_ms'] = loss, rtt
                f.write(','.join(str(s[k]) for k in header) + '\n')
                info("    step %2d  pos=%g,%g  dist=%.1fm  rssi=%s  %s\n"
                     % (i, x, y, s['distance_m'], s['rssi_dbm'],
                        ('loss=%s%% rtt=%s' % (loss, rtt)) if target else ''))
        except KeyboardInterrupt:
            info("\n*** survey interrupted\n")
        f.close()
        info("*** survey saved: %s\n" % path)

    def do_measure(self, line):
        "Ping between two nodes.  Usage: measure <src> <dst> [count]"
        args = line.split()
        if len(args) < 2:
            info("usage: measure <src> <dst> [count]\n")
            return
        src, dst = self._node(args[0]), self._node(args[1])
        if src is None or dst is None:
            return
        count = int(args[2]) if len(args) > 2 else 5
        loss, rtt = ping_once(src, dst.IP(), count)
        info("    %s -> %s : loss=%s%%  avg rtt=%s ms\n"
             % (src.name, dst.name, loss, rtt))

    def do_refresh(self, line):
        "Repaint the graph window."
        pump_graph()

    def postcmd(self, stop, line):
        pump_graph()
        return stop


def print_help():
    info("\n*** Live-edit commands (graph updates immediately):\n"
         "    move    <node> <x> <y> [z]       move a station or AP\n"
         "    range   <node> <meters>          change range\n"
         "    txpower <node> <dBm>             change tx power\n"
         "*** Data commands:\n"
         "    rssi    [sta ...]                RSSI / distance / AP now\n"
         "    watch   <sec> [interval] [sta]   print RSSI repeatedly\n"
         "    log start <file.csv> [interval] [sta ...]  /  log stop\n"
         "    survey  <sta> <x1> <y1> <x2> <y2> <steps> [file.csv] [ping_target]\n"
         "    measure <src> <dst> [count]      ping loss / rtt\n"
         "    CSV files go to: %s\n"
         "*** Other: refresh, pingall, xterm sta1, exit\n\n" % DATA_DIR)


def custom_topology():
    patch_graph()
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

    if SHOW_GRAPH:
        net.plotGraph(max_x=CANVAS_MAX_X, max_y=CANVAS_MAX_Y)

    build_mobility(net, stas)

    info("*** Starting network\n")
    net.build()
    for ap in aps.values():
        ap.start([])          # empty list = no controller

    patch_graph()             # in case mn_wifi.plot loaded during build
    for node in list(aps.values()) + list(stas.values()):
        redraw_node(node, pump=False)
    pump_graph()

    print_help()
    info("*** Running CLI\n")
    LiveCLI(net)

    if LiveCLI.logger:
        LiveCLI.logger.stop()

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    custom_topology()