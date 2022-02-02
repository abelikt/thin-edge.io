#!/bin/bash

set -e

echo "Configuring Bridge"

# Squelch the https:// from the url
URL=$(echo $C8YURL | cut -c 9- - )

sudo tedge cert remove

sudo tedge cert create --device-id=$C8YDEVICE

sudo tedge cert show

sudo tedge config set c8y.url $URL

sudo tedge config set c8y.root.cert.path /etc/ssl/certs

sudo tedge config set az.url $IOTHUBNAME.azure-devices.net

sudo tedge config set az.root.cert.path /etc/ssl/certs/Baltimore_CyberTrust_Root.pem

sudo tedge config list

# Note: This will always upload a new certificate. From time to time
# we should delete the old ones in c8y
sudo -E tedge cert upload c8y --user $C8YUSERNAME

cat /etc/mosquitto/mosquitto.conf


# TODO Move all this to another place

# for now abuse the pysys-env
python3 -m venv ~/env-pysys
source ~/env-pysys/bin/activate
pip3 install -r tests/requirements.txt

# Delete the device
python3 ./ci/delete_current_device_c8y.py

# Connect and disconnect so that we can retrive a new device ID
sudo tedge connect c8y
sudo tedge disconnect c8y
deactivate

# Care about Cumulocity device ID

./ci/find_device_id.py --tenant $C8YTENANT --user $C8YUSERNAME --device $C8YDEVICE --url $URL > ~/C8YDEVICEID

C8YDEVICEID=$(cat ~/C8YDEVICEID)
echo "The current device ID is (read from home directory): " $C8YDEVICEID

# For now, we create that file here:
# TODO There is probably a better solution, e.g. also for developer setups
echo "export C8YDEVICEID=$(cat ~/C8YDEVICEID)" > ~/c8yenv.sh
chmod +x ~/c8yenv.sh

