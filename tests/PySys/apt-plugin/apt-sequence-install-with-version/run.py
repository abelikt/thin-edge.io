import sys
import os
import time

sys.path.append("apt-plugin")
from environment_apt_plugin import AptPlugin

"""
Validate apt plugin install use case

When we prepare
When we install a package
When we finalize
Then the package is installed

Issue:
whenever there is a parameter --version the output will be "apt-install 0.1.0"

sudo /etc/tedge/sm-plugins/apt install rolldice 1.16-1+b3 --version
apt-install 0.1.0


"""


class AptPluginInstallTest(AptPlugin):
    def setup(self):
        super().setup()

        self.package = "rolldice"
        # Debian: buster 1.16-1+b1
        # Debian: bullseye 1.16-1+b3
        self.version = "1.16-1+b3"  # this test will fail if the version changes
        self.apt_remove(self.package)
        self.assert_isinstalled(self.package, False)
        self.addCleanupFunction(self.cleanup_prepare)

    def execute(self):
        self.plugin_cmd("prepare", "outp_prepare", 0)
        self.plugin_cmd(
            "install", "outp_install", 0, argument=self.package, version=self.version
        )
        self.plugin_cmd("finalize", "outp_finalize", 0)

    def validate(self):
        self.assert_isinstalled(self.package, True)
        # This is evaluated as regex therefore we need to excape the plus sign
        # Expression (1|3) matches either 1 or 3 for debian buster or bullseye
        self.assertGrep(
            "outp_check_1.out",
            '{"name":"rolldice","version":"1.16-1\+b(1|3)"}',
            contains=True,
        )

    def cleanup_prepare(self):
        self.apt_remove(self.package)
