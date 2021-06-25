import sys
import time

sys.path.append("environments")
from environment_edge_test_c8y import Environment_Edge_Test_c8y

"""
Edge test case / deterministic internal chaos

Given a configured system with configured certificate
When we connect to c8y and publish values
when we wait for 5s
When we disable the tedge mapper for 5 seconds
Then we validate all the data that we have published

This test needs mosquitto configured to use the ethernet interface
with bridge_bind_address
"""


class Edge_test_network_down(Environment_Edge_Test_c8y):
    def setup(self):
        super().setup()
        self.samples = "300"
        self.delay = "100"
        self.timeslot = "35"
        self.style = "JSON"

    def execute(self):
        super().execute()
        self.log.debug("C8y Roundtrip Execute")

        time.sleep(5)

        chaos = True

        #interface = "enp0s31f6" # Michaels laptop
        interface = "eth0" # Rpi

        if chaos:
            connect = self.startProcess(
                command=self.sudo,
                arguments=["ip", "link", "set", interface, "down"],
                stdouterr="ip_down",
            )

            time.sleep(5)

            connect = self.startProcess(
                command=self.sudo,
                arguments=["ip", "link", "set", interface, "up"],
                stdouterr="ip_up",
            )

        self.waitForBackgroundProcesses()

