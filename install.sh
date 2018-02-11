#!/bin/bash

sudo mkdir -p /etc/slack_notifier/templates.d/
sudo cp ./slack_notifier/slack_notifier.py /usr/local/bin/slack_notifier
sudo cp -r ./templates.d/ /etc/slack_notifier/templates.d/
sudo chmod a+x /usr/local/bin/slack_notifier
sudo chmod a+w -R /etc/slack_notifier/
cp ./slack_notifier.service /etc/systemd/system/multi-user.target.wants/
systemctl daemon-reload
systemctl enable slack_notifier.service
