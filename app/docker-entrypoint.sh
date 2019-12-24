#!/bin/bash

# Copy all files and folders from the staging area to PVC
cp -R /tmp/NATS/stage /NATS
cp -R /tmp/NATS/scripts /NATS
cp -R /tmp/NATS/log /NATS
cp -R /tmp/NATS/bin /NATS

# Set permissions
chown -R runner:runner /NATS/stage
chown -R runner:runner /NATS/scripts
chown -R runner:runner /NATS/log
chown -R runner:runner /NATS/bin

exec "$@"
