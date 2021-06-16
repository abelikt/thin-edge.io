from pysys.basetest import BaseTest

import time
import json

"""
Validate a tedge-mapper-az message with timestamp that is published
on az/messages/events/

Given a configured system
When we start the tedge-mapper-az systemctl service
When we start tedge sub with sudo in the background
When we publish a Thin Edge JSON message
Then we kill tedge sub with sudo as it is running with a different user account
Then we validate the JSON message in the output of tedge sub
Then we stop the tedge-mapper-az systemctl service

"""

class TedgeMapperAzBed(BaseTest):
    def setup(self):
        self.tedge = "/usr/bin/tedge"
        self.sudo = "/usr/bin/sudo"

        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "start", "tedge-mapper-az"],
            stdouterr="tedge_mapper_az",
        )

        self.addCleanupFunction(self.mapper_cleanup)

    def mapper_cleanup(self):
        self.log.info("mapper_cleanup")
        mapper = self.startProcess(
            command=self.sudo,
            arguments=["systemctl", "stop", "tedge-mapper-az"],
            stdouterr="tedge_mapper_az",
        )

    def execute(self):

        sub = self.startProcess(
            command=self.sudo,
            arguments=[self.tedge, "mqtt", "sub", "--no-topic", "az/messages/events/"],
            stdouterr="tedge_sub",
            background=True,
        )

        # Wait for a small amount of time to give tedge sub time
        # to initialize. This is a heuristic measure.
        # Without an additional wait we observe failures in 1% of the test
        # runs.
        time.sleep(0.1)

        pub = self.startProcess(
            command=self.sudo,
            arguments=[self.tedge, "mqtt", "pub",
                       self.topic , self.message],
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
        f = open(self.output + '/tedge_sub.out', 'r')
        self.thin_edge_json = json.load(f)

    def assert_json(self, key, value):
        self.assertThat('actual == expected', actual = self.thin_edge_json[key], expected = value)

class TedgeMapperAzWithTimestamp(TedgeMapperAzBed):

    def setup(self):
        super().setup()
        self.topic = "tedge/measurements"
        self.message = '{"temperature": 12, "time": "2021-06-15T17:01:15.806181503+02:00"}'

    def validate(self):
        super().validate()

        self.assert_json( 'temperature' , 12)
        self.assert_json( 'time' , '2021-06-15T17:01:15.806181503+02:00')
