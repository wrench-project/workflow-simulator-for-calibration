#!/bin/bash 
#
# This script installs EVERYTHING, so that we can run things bare-metal, bare-metal but using
# Docker for the simulator, or all inside Docker
#
set -e

# Update repo
sudo apt-get update

# Install stuff
sudo apt-get install -y cmake

# Install python 3.9
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.9
sudo update-alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.9 10
sudo apt-get install -y python3-pip
sudo apt-get install -y --reinstall python3.9-distutils

# Install WfCommons
sudo apt-get install -y gfortran
sudo apt-get install -y libopenblas-dev
pushd /tmp && git clone https://github.com/wfcommons/wfcommons.git && cd wfcommons && git checkout 29c69989fe5701bc07eb66c0077531f60e8a4414 && sudo python3 -m pip install . && cd .. && rm -rf wfcommons && popd

# Install DeepHyper
python3 -m pip install -r calibration/requirements.txt

# Install latex stuff
sudo apt-get install -y texlive-base texlive-latex-extra cm-super dvipng

# Install WRENCH stuff
pushd /tmp && wget --no-check-certificate https://boostorg.jfrog.io/artifactory/main/release/1.80.0/source/boost_1_80_0.tar.gz && tar -xvf boost_1_80_0.tar.gz && cd boost_1_80_0 && ./bootstrap.sh && ./b2 && sudo ./b2 install && cd .. && sudo /bin/rm -rf boost_1_80_0* && popd

pushd /tmp && /bin/rm -rf ./simgrid && git clone https://framagit.org/simgrid/simgrid.git && cd simgrid && mkdir build && cd build && cmake .. && make -j16 && sudo make install && cd ../.. && sudo /bin/rm -rf simgrid && popd

pushd /tmp && wget --no-check-certificate https://github.com/nlohmann/json/archive/refs/tags/v3.10.5.tar.gz && tar -xf v3.10.5.tar.gz && cd json-3.10.5 && cmake . && make -j16 && sudo make install && cd .. && sudo /bin/rm -rf v3.10.5* json-3.10.5 && popd

pushd /tmp && /bin/rm -rf ./wrench && git clone https://github.com/wrench-project/wrench.git && cd wrench && mkdir build && cd build && cmake .. && make -j16 && sudo make install && cd .. && sudo /bin/rm -rf wrench && popd

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/

# Install this repo
sudo rm -rf ./build && mkdir ./build && cd ./build && cmake .. && make -j4 && sudo make install && cd .. && sudo rm -rf build

# Install Docker
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
sudo /bin/rm -f /etc/apt/keyrings/docker.gpg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo groupadd --force docker
sudo usermod -aG docker `whoami`

# Done
echo ""
echo ""
echo "****************************************************************************"
echo "NOTE ABOUT USING DOCKER, WHICH IS OPTIONAL:"
echo ""
echo "If you intend to use Docker, and 'docker ps' gives you some 'not allowed' error, you should try to log out and log back in, which _may_ make it possible to run docker without sudo. If not, then you may be on a VM and may need to reboot it. Once you know you can run Docker without sudo, you should do:"
echo "  docker pull wrenchproject/workflow-calibration"
echo ""
echo "You will then be ready to run the calibration script, using Docker e.g.:"
echo "  ./calibration/calibrate.py --docker -c ./calibration/config.json"


