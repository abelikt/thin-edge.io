import sys

sys.path.append("apt-plugin")
from environment_apt_plugin import AptPlugin

"""
Validate apt plugin remove fails

When we remove a non exiisting package
Then we expect an error code from the plugin
"""


class AptPluginRemoveTestFail(AptPlugin):
    def setup(self):
        super().setup()
        self.assert_isinstalled("notapackage", False)

    def execute(self):
        self.plugin_cmd("remove", "outp_remove", 2, "notapackage")

    def validate(self):
        self.assert_isinstalled("notapackage", False)
