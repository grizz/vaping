from __future__ import absolute_import

import vaping
import vaping.config
import vaping.io

try:
    import vodka
    import vodka.data
except ImportError:
    pass

try:
    import graphsrv
    import graphsrv.group
except ImportError:
    graphsrv = None



def probe_to_graphsrv(probe):
    """
    takes a probe instance and generates
    a graphsrv data group for it using the
    probe's config
    """

    config = probe.config

    # manual group set up via `group` config key

    if "group" in config:
        source, group = config["group"].split(".")
        group_field = config.get("group_field", "host")
        group_value = config[group_field]
        graphsrv.group.add(source, group, {group_value:{group_field:group_value}}, **config)
        return

    # automatic group setup for fping
    # FIXME: this should be somehow more dynamic

    for k, v in list(config.items()):
        if isinstance(v, dict) and "hosts" in v:
            r = {}
            for host in v.get("hosts"):
                if isinstance(host, dict):
                    r[host["host"]] = host
                else:
                    r[host] = {"host":host}
            graphsrv.group.add(probe.name, k, r, **v)


@vaping.plugin.register('vodka')
class VodkaPlugin(vaping.plugins.EmitBase):

    """
    Plugin that emits to vodka data
    """

    def init(self):
        self._is_started = False
        self._is_starting = False

    def start(self):
        """
        We are delaying the vodka startup to
        circumvent some sort of race condition that
        causes flask to be unresponsive when running
        with py3 (and probably certain versions of py2.7)

        FIXME: look into this more
        """
        if self._is_starting:
            return

        self._is_starting = True

        # actually start vodka plugin after a short sleep
        vaping.io.sleep(0.5)
        self._start()

    def _start(self):

        if self._is_started:
            return
        self._is_started = True
        vodka.run(self.config, self.vaping.config)

        if graphsrv:
            # if graphsrv is installed proceed to generate
            # target configurations for it from probe config

            for node in self.vaping.config.get("probes", []):
                probe = vaping.plugin.get_probe(node, self.vaping)
                probe_to_graphsrv(probe)


    def emit(self, message):
        if not self._is_started:
            self.start()

        vodka.data.handle(message.get("type"), message, data_id=message.get("source"), caller=self)
