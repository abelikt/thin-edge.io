import sys
import time

sys.path.append("environments")
from environment_edge_test_c8y import Environment_Edge_Test_c8y

"""
Edge test case / deterministic internal chaos

Given a configured system with configured certificate
When we connect to c8y and publish values
when we wait for 5s
When we disable the network interface for 5 seconds
Then we validate all the data that we have published
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

        if chaos:
            tedge_mapper1 = self.startProcess(
                command=self.sudo,
                arguments=["systemctl", "stop", "tedge-mapper-c8y"],
                stdouterr="tedge_mapper_stop",
            )

            time.sleep(5)

            tedge_mapper_2 = self.startProcess(
                command=self.sudo,
                arguments=["systemctl", "start", "tedge-mapper-c8y"],
                stdouterr="tedge_mapper_start",
            )

        self.waitForBackgroundProcesses()

