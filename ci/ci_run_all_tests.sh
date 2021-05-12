#!/usr/bin/bash

# Run all available system-tests.
# Note: Needs a bash shell to run
#
# Expected environment variables to be set:
# C8YPASS : Cumulocity password
# C8YUSERNAME : Cumolocity username
# C8YTENANT : Cumolocity tenant
# C8YDEVICE : The device name
# C8YDEVICEID : The device ID in Cumolocity
# TIMEZONE : Your timezone (temporary)
# TEBASEDIR : Base directory for the Thin-Edge repo
# EXAMPLEDIR : The direcory of the sawtooth example

# Adding sbin seems to be necessary for non Raspberry P OS systems as Debian or Ubuntu
PATH=$PATH:/usr/sbin

echo "Disconnect old bridge"

# Disconnect - may fail if not there
sudo tedge disconnect c8y

# From now on exit if a command exits with a non-zero status.
# Commands above are allowed to fail
set -e

cd $TEBASEDIR

# Check if clients are installed. If not, run:
# sudo apt-get install mosquitto-clients

dpkg -s mosquitto-clients

# Install necessary packages
# TODO: Not available on buster
# sudo apt install -y junitparser

./ci/configure_bridge.sh

# Run all PySys tests

python3 -m venv ~/env-pysys
source ~/env-pysys/bin/activate

pip3 install -r tests/requirements.txt

cd tests/PySys/

# Don't use -v DEBUG as this will might reveal secret credentials

pysys.py run --record

#pysys.py run --record -c 100 c8y_restart_bridge

# TODO: Not available on buster
#junitparser merge __pysys_junit_xml/* all_tests_junit.xml

# TODO: Not available on buster
#junit2html all_tests_junit.xml all_tests_junit.html

deactivate
