
import json
import sys
import time
import jsonschema
from pysys.basetest import BaseTest

"""
Testbed for tedge mappers.
Actual testcases derive from this testbed class.

"""

# TODO : publish and subscribe with mosquitto clients ?
# TODO Make more generic c8y, az, collectd
# TODO Subscribe with mosquitto client with timeout -> avoid kill
# TODO How to wait for collectd ?
# TODO How to specify unprecise e.g. with ANY


class MapperTestbedC8y(BaseTest):

    # JSON schema to validate messages:
    # Will check for this pattern
    # {'type': 'ThinEdgeMeasurement', 'temperature': {'temperature': {'value': 12}}, 'time': '2021-06-15T17:01:15.806181503+02:00'}
    tedgeschema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/product.schema.json",
        "title": "ThinEdgeMeasurement",
        "description": "A thin edge measurement",
        "type": "object",
        "properties": {
            "type": {"description": "The type", "type": "string"},
            "temperature": {
                "description": "The temperature",
                "type": "object",
                "properties": {
                    "type": {
                        "temperature": "The type",
                        "type": "object",
                        "properties": {
                            "type": {"value": "The type", "type": "integer"},
                        },
                        "required": ["value"],
                    },
                },
                "required": ["temperature"],
            },
            "time": {"description": "The time", "type": "string"},
        },
        "required": ["type", "temperature", "time"],
    }

    def setup(self):
        """Setup Testcase
        Stop all other mappers and start the c8y mapper
        """
        self.tedge = "/usr/bin/tedge"
        self.sudo = "/usr/bin/sudo"
        self.tedge = "/usr/bin/tedge"
        self.tedge_mapper_c8y = "tedge-mapper-c8y"
        self.tedge_mapper_az = "tedge-mapper-az"
        self.sudo = "/usr/bin/sudo"
        self.systemctl = "/usr/bin/systemctl"
        self.topic_subscribe = "c8y/measurement/measurements/create"
        self.topic_publish = "tedge/measurements"
        self.topic_errors = "tedge/errors"

        # Check if tedge-mappersare in disabled state
        serv_mapper = self.startProcess(
            command=self.systemctl,
            arguments=["status", "collectd-mapper"],
            stdouterr="serv_mapper1",
            expectedExitStatus="==3",  # 3: disabled
        )

        serv_mapper = self.startProcess(
            command=self.systemctl,
            arguments=["status", self.tedge_mapper_c8y],
            stdouterr="serv_mapper1",
            expectedExitStatus="==3",  # 3: disabled
        )

        serv_mapper = self.startProcess(
            command=self.systemctl,
            arguments=["status", self.tedge_mapper_az],
            stdouterr="serv_mapper1",
            expectedExitStatus="==3",  # 3: disabled
        )

        # Start only the c8y mapper
        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "start", "tedge-mapper-c8y"],
            stdouterr="tedge_mapper_c8y",
        )

        self.addCleanupFunction(self.mapper_cleanup)

    def execute(self):
        """Execute testcase: Subscribe to topic and erros.
        Exchange message
        """

        sub = self.startProcess(
            command=self.sudo,
            arguments=[
                self.tedge,
                "mqtt",
                "sub",
                "--no-topic",
                self.topic_subscribe,
            ],
            stdouterr="tedge_sub",
            background=True,
        )

        sub_errror = self.startProcess(
            command=self.sudo,
            arguments=[self.tedge, "mqtt", "sub", "--no-topic", self.topic_errors],
            stdouterr="tedge_sub_error",
            background=True,
        )

        # Wait for a small amount of time to give tedge sub time
        # to initialize. This is a heuristic measure.
        # Without an additional wait we observe failures in 1% of the test
        # runs.
        time.sleep(0.1)

        pub = self.startProcess(
            command=self.sudo,
            arguments=[self.tedge, "mqtt", "pub", self.topic_publish, self.message],
            stdouterr="tedge_temp",
        )

        # Kill the subscribers processes explicitly with sudo as PySys does
        # not have the rights to do it
        kill = self.startProcess(
            command=self.sudo,
            arguments=["killall", "tedge"],
            stdouterr="kill_out",
        )

    def validate(self):

        # open the topic and read data into variable c8y_json
        with open(self.output + "/tedge_sub.out", "r") as outfile:
            data = outfile.read()
            self.log.info(data)
            self.c8y_json = json.loads(data)
            self.log.info(self.c8y_json)

        # open the error topic and read data into variable errors
        with open(self.output + "/tedge_sub_error.out", "r") as outfile:
            data = outfile.read()
            self.log.info(data)
            if data:
                self.errors = json.loads(data)
                self.log.info(self.errors)
            else:
                self.errors = None
                self.log.info("No errors")

    def mapper_cleanup(self):
        """Cleanup : Stop the tedge mapper"""

        self.log.info("mapper_cleanup")
        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "stop", "tedge-mapper-c8y"],
            stdouterr="tedge_mapper_c8y",
        )

    def assert_json_key(self, key, value):
        """Asssert that a key has a value in the top structure in json"""
        self.assertThat("actual == expected", actual=self.c8y_json[key], expected=value)

    def assert_json(self, actual, value):
        """Simple assertation mapper to assert That"""
        self.assertThat("actual == expected", actual=actual, expected=value)

    def assert_no_error(self):
        """Assert that there are no errors in the error topic"""
        self.assertThat("actual == expected", actual=self.errors, expected=None)

    def validate_json(self):
        """Validate received message against the json schema"""
        jsonschema.validate(instance=self.c8y_json, schema=self.tedgeschema)

