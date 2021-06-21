
import sys
sys.path.append("mapper_testbed")

from pysys.basetest import BaseTest

from mapper_testbed_c8y import MapperTestbedC8y


"""
Validate a tedge-mapper-c8y message that is published
on c8y/measurement/measurements/create

"""

class TedgeMapperC8y(MapperTestbedC8y):
    def setup(self):
        super().setup()

        # The message that we send to the mapper
        self.message = (
            '{"temperature": 12, "time": "2021-06-15T17:01:15.806181503+02:00"}'
        )

        # The message that we expect back from the mapper
        self.expect = {
            "type": "ThinEdgeMeasurement",
            "temperature": {"temperature": {"value": 12}},
            "time": "2021-06-15T17:01:15.806181503+02:00",
        }

    def validate(self):
        super().validate()

        # Validate that the json, we received from the mapper is valid accoring to our schema
        self.validate_json()

        # Asserting the values is enough here
        self.assert_json(self.c8y_json["temperature"]["temperature"]["value"], 12)
        self.assert_json_key("time", "2021-06-15T17:01:15.806181503+02:00")

        # Assert that we have received no errors on the error topic
        self.assert_no_error()

        # Direct comparison, depends on the use-case
        assert self.c8y_json == self.expect
