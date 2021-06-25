import sys
import time

sys.path.append("environments")
from environment_edge_test_c8y import Environment_Edge_Test_c8y

"""
Edge test case / deterministic internal chaos

Given a configured system with configured certificate
When we connect to c8y and publish values
when we wait for 5s
When we disable mosquitto for 5 seconds
Then we validate all the data that we have published

This testcase will only pass, if the publisher does not ignore the errors

[2021-06-25T12:46:45Z ERROR sawtooth_publisher] System error: MQTT connection error: Mqtt state: Io error Custom { kind: ConnectionAborted, error: "connection closed by peer" }
[2021-06-25T12:46:46Z ERROR sawtooth_publisher] System error: MQTT connection error: I/O: Connection refused (os error 111)
[2021-06-25T12:46:47Z ERROR sawtooth_publisher] System error: MQTT connection error: I/O: Connection refused (os error 111)
[2021-06-25T12:46:48Z ERROR sawtooth_publisher] System error: MQTT connection error: I/O: Connection refused (os error 111)

"""


class Edge_test_network_down(Environment_Edge_Test_c8y):
    def setup(self):
        super().setup()
        self.samples = "200"
        self.delay = "100"
        self.timeslot = "25"
        self.style = "JSON"

    def execute(self):
        super().execute()
        self.log.debug("C8y Roundtrip Execute")

        time.sleep(5)

        chaos = True

        if chaos:
            tedge_mapper1 = self.startProcess(
                command=self.sudo,
                arguments=["systemctl", "stop", "mosquitto"],
                stdouterr="tedge_mapper_stop",
            )

            time.sleep(5)

            tedge_mapper_2 = self.startProcess(
                command=self.sudo,
                arguments=["systemctl", "start", "mosquitto"],
                stdouterr="tedge_mapper_start",
            )

        self.waitForBackgroundProcesses()

