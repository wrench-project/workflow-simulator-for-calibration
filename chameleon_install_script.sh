#!/bin/bash 
#
set -e

# Update repo
sudo apt-get update

# Install python 3.9
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.9
sudo update-alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.9 10
sudo apt-get install -y python3-pip
sudo apt-get install -y --reinstall python3.9-distutils

# Install WfCommons
sudo apt-get install -y gfortran
sudo apt-get install -y libopenblas-dev
git clone https://github.com/wfcommons/wfcommons.git && cd wfcommons && git checkout 29c69989fe5701bc07eb66c0077531f60e8a4414 && sudo python3 -m pip install . && cd .. && rm -rf wfcommons

# Install DeepHyper
python3 -m pip install -r calibration/requirements.txt

# Install Docker
sudo apt-get remove -y docker docker-engine docker.io containerd runc
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo groupadd docker
sudo usermod -aG docker $USER
sudo newgrp docker

# Done
echo "You should now be able to run: ./calibration/calibrate.py -c ./calibration/config.json"


