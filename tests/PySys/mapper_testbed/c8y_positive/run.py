from pysys.basetest import BaseTest

import time
import json

"""
Validate a tedge-mapper-c8y message that is published
on c8y/measurement/measurements/create

Given a configured system
When we start the tedge-mapper-c8y systemctl service
When we start tedge sub with sudo in the background
When we publish a Thin Edge JSON message
Then we kill tedge sub with sudo as it is running with a different user account
Then we validate the JSON message in the output of tedge sub
Then we stop the tedge-mapper-c8y systemctl service

"""


class TedgeMapperC8yBed(BaseTest):
    def setup(self):
        self.tedge = "/usr/bin/tedge"
        self.sudo = "/usr/bin/sudo"

        self.tedge = "/usr/bin/tedge"
        self.tedge_mapper_c8y = "tedge-mapper-c8y"
        self.tedge_mapper_az = "tedge-mapper-az"
        self.sudo = "/usr/bin/sudo"
        self.systemctl = "/usr/bin/systemctl"

        # Check if tedge-mapper is in disabled state
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

        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "start", "tedge-mapper-c8y"],
            stdouterr="tedge_mapper_c8y",
        )

        self.addCleanupFunction(self.mapper_cleanup)

    def execute(self):
        sub = self.startProcess(
            command=self.sudo,
            arguments=[
                self.tedge,
                "mqtt",
                "sub",
                "--no-topic",
                "c8y/measurement/measurements/create",
            ],
            stdouterr="tedge_sub",
            background=True,
        )

        sub_errror = self.startProcess(
            command=self.sudo,
            arguments=[self.tedge, "mqtt", "sub", "--no-topic", "tedge/errors"],
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
            arguments=[self.tedge, "mqtt", "pub", "tedge/measurements", self.message],
            stdouterr="tedge_temp",
        )

        # Kill the subscriber process explicitly with sudo as PySys does
        # not have the rights to do it
        kill = self.startProcess(
            command=self.sudo,
            arguments=["killall", "tedge"],
            stdouterr="kill_out",
        )

    def validate(self):
        f = open(self.output + "/tedge_sub.out", "r")
        data = f.read()
        self.log.info(data)
        self.c8y_json = json.loads(data)
        self.log.info(self.c8y_json)

        f = open(self.output + "/tedge_sub_error.out", "r")
        data = f.read()
        self.log.info(data)
        if data:
            self.errors = json.loads(data)
            self.log.info(self.errors)
        else:
            self.errors = None
            self.log.info("No errors")

    def mapper_cleanup(self):
        self.log.info("mapper_cleanup")
        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "stop", "tedge-mapper-c8y"],
            stdouterr="tedge_mapper_c8y",
        )

    def assert_json_key(self, key, value):
        self.assertThat("actual == expected", actual=self.c8y_json[key], expected=value)

    def assert_json(self, key, value):
        self.assertThat("actual == expected", actual=key, expected=value)

    def assert_no_error(self):
        self.assertThat("actual == expected", actual=self.errors, expected=None)


class TedgeMapperC8y(TedgeMapperC8yBed):
    def setup(self):
        super().setup()
        self.message = (
            '{"temperature": 12, "time": "2021-06-15T17:01:15.806181503+02:00"}'
        )

    def validate(self):

        super().validate()

        # Will expect:
        # {'type': 'ThinEdgeMeasurement', 'temperature': {'temperature': {'value': 12}}, 'time': '2021-06-15T17:01:15.806181503+02:00'}

        self.assert_json_key("type", "ThinEdgeMeasurement")
        self.assert_json(self.c8y_json["temperature"]["temperature"]["value"], 12)
        self.assert_json_key("time", "2021-06-15T17:01:15.806181503+02:00")
        self.assert_no_error()
