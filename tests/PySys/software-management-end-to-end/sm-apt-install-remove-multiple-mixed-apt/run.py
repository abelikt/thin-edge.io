from pysys.basetest import BaseTest

import time

"""
Validate end to end behaviour for the apt plugin for multiple packages

When we install a bunch of packages
Then they are installed
When we deinstall them again
Then they are not installed
"""

import json
import requests
import time
import sys

sys.path.append("software-management-end-to-end")
from environment_sm_management import SmManagement


class PySysTest(SmManagement):
    def setup(self):
        super().setup()

        self.assertThat("True == value", value=self.check_isinstalled("apple"))
        self.assertThat("True == value", value=self.check_isinstalled("banana"))
        self.assertThat("True == value", value=self.check_isinstalled("cherry"))
        self.assertThat("False == value", value=self.check_isinstalled("asciijump"))

    def execute(self):

        pkgid = {
            # apt
            "asciijump": "5475278",
            "robotfindskitten": "5473003",
            "squirrel3": "5474871",
            "rolldice": "5445239",
        }

        act = "install"
        action = [
            {
                "action": act,
                "id": pkgid["asciijump"],
                "name": "asciijump",
                "url": " ",
                "version": "::apt",
            },
        ]

        self.trigger_action_json(action)

        self.wait_until_succcess()

        self.assertThat("True == value", value=self.check_isinstalled("apple"))
        self.assertThat("True == value", value=self.check_isinstalled("banana"))
        self.assertThat("True == value", value=self.check_isinstalled("cherry"))
        self.assertThat("True == value", value=self.check_isinstalled("asciijump"))

        act = "delete"
        action = [
            {
                "action": act,
                "id": pkgid["asciijump"],
                "name": "asciijump",
                "url": " ",
                "version": "::apt",
            },
        ]

        self.trigger_action_json(action)

        self.wait_until_succcess()

    def validate(self):

        self.assertThat("True == value", value=self.check_isinstalled("apple"))
        self.assertThat("True == value", value=self.check_isinstalled("banana"))
        self.assertThat("True == value", value=self.check_isinstalled("cherry"))
        self.assertThat("False == value", value=self.check_isinstalled("asciijump"))
