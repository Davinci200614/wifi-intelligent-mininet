#!/bin/bash
sudo apt update
sudo apt install -y git python3-pip openvswitch-switch
if [ ! -d "src/top/libs/mininet-wifi" ]; then
    git clone https://github.com/intrig-unicamp/mininet-wifi.git
fi
mv mininet-wifi src/top/libs/mininet-wifi