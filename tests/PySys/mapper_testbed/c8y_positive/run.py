from pysys.basetest import BaseTest
import jsonschema

import sys
sys.path.append("mapper_testbed")
from mapper_testbed_c8y import MapperTestbedC8y


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

class TedgeMapperC8y(MapperTestbedC8y):
    def setup(self):
        super().setup()
        self.message = (
            '{"temperature": 12, "time": "2021-06-15T17:01:15.806181503+02:00"}'
        )

        self.expect = {
            "type": "ThinEdgeMeasurement",
            "temperature": {"temperature": {"value": 12}},
            "time": "2021-06-15T17:01:15.806181503+02:00",
        }

    def validate(self):

        super().validate()

        # Will expect:
        # {'type': 'ThinEdgeMeasurement', 'temperature': {'temperature': {'value': 12}}, 'time': '2021-06-15T17:01:15.806181503+02:00'}

        self.assert_json_key("type", "ThinEdgeMeasurement")
        self.assert_json(self.c8y_json["temperature"]["temperature"]["value"], 12)
        self.assert_json_key("time", "2021-06-15T17:01:15.806181503+02:00")
        self.assert_no_error()

        jsonschema.validate(instance=self.c8y_json, schema=self.tedgeschema)

        # also possible
        assert self.c8y_json == self.expect
