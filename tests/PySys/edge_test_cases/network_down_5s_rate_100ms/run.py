import sys
import time

sys.path.append("environments")
from environment_edge_test_c8y import Environment_Edge_Test_c8y

"""
Roundtrip test C8y 400 samples 20ms delay

Given a configured system with configured certificate
When we derive from EnvironmentC8y
When we run the smoketest for JSON publishing with defaults a size of 400, 20ms delay
Then we validate the data from C8y
"""


class Edge_test_network_down(Environment_Edge_Test_c8y):
    def setup(self):
        super().setup()
        self.samples = "1000"
        self.delay = "20"
        self.timeslot = "30"
        self.style = "JSON"

    def execute(self):
        super().execute()
        self.log.debug("C8y Roundtrip Execute")

        time.sleep(5)

        chaos = True
        if chaos:
            connect = self.startProcess(
                command=self.sudo,
                arguments=["ip", "link", "set", "enp0s31f6", "down"],
                stdouterr="ip_down",
            )

            time.sleep(1)

            connect = self.startProcess(
                command=self.sudo,
                arguments=["ip", "link", "set", "enp0s31f6", "up"],
                stdouterr="ip_up",
            )

        self.waitForBackgroundProcesses()

