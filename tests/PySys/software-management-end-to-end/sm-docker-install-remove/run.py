from pysys.basetest import BaseTest

import time

"""
Validate end to end behaviour for the apt plugin for installation and removal of packages

For the apt plugin with ::apt

When we install a package
Then it is installed
When we deinstall it again
Then it is not installed
"""

import json
import requests
import time
import sys

sys.path.append("software-management-end-to-end")
from environment_sm_management import SoftwareManagement


class PySysTest(SoftwareManagement):
    def setup(self):
        super().setup()
        self.assertThat("False == value", value=self.check_is_installed("alpine"))

    def execute(self):

        self.trigger_action(
            "alpine", self.get_pkgid("alpine"), "::docker", "notanurl", "install"
        )

        self.wait_until_succcess()

        self.assertThat("True == value", value=self.check_is_installed("rolldice"))

        self.trigger_action(
            "alpine", self.get_pkgid("alpine"), "::docker", "notanurl", "delete"
        )

        self.wait_until_succcess()

    def validate(self):

        self.assertThat("False == value", value=self.check_is_installed("alpine"))
