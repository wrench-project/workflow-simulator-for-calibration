FROM amd64/ubuntu:jammy
#FROM i386/ubuntu:focal
#FROM rayproject/ray

LABEL org.opencontainers.image.authors="henric@hawaii.edu"

USER root

# add repositories
RUN apt-get update

# set timezone
RUN echo "America/Los_Angeles" > /etc/timezone && export DEBIAN_FRONTEND=noninteractive && apt-get install -y tzdata

# install compiler
RUN apt-get -y install gcc g++

# build environment
RUN apt-get -y install pkg-config git wget sudo curl vim make cmake cmake-data

# latest cmake
#RUN wget --no-check-certificate https://github.com/Kitware/CMake/releases/download/v3.25.2/cmake-3.25.2.tar.gz && tar -xzf cmake-3.25.2.tar.gz && cd cmake-3.25.2 && ./bootstrap -- -DCMAKE_USE_OPENSSL=OFF && make -j4 && make install && cd .. && rm -rf cmake-3.25.2.tar.gz && rm -rf cmake-3.25.2


# install python 3.9
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get install -y python3.9
RUN update-alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.9 10
RUN apt-get install -y python3-pip
RUN apt-get install -y --reinstall python3.9-distutils

#################################################
# WRENCH and its dependencies
#################################################

# set root's environment variable
ENV CXX="g++" CC="gcc"
WORKDIR /tmp

# install Boost 1.80
#RUN apt-get install -y libboost-all-dev
RUN wget --no-check-certificate https://boostorg.jfrog.io/artifactory/main/release/1.80.0/source/boost_1_80_0.tar.gz && tar -xvf boost_1_80_0.tar.gz && cd boost_1_80_0 && ./bootstrap.sh && ./b2 && ./b2 install && cd .. && rm -rf boost_1_80_0

# install SimGrid master
RUN git clone https://framagit.org/simgrid/simgrid.git && cd simgrid && git checkout 3863ea3407b8209a66dded84e28001f24225682c && mkdir build && cd build && cmake .. && make -j4 && make install && cd ../.. && rm -rf simgrid

# install json for modern c++
RUN wget --no-check-certificate https://github.com/nlohmann/json/archive/refs/tags/v3.10.5.tar.gz && tar -xf v3.10.5.tar.gz && cd json-3.10.5 && cmake . && make -j4 && make install && cd .. && rm -rf v3.10.5* json-3.10.5

# install WRENCH
RUN git clone https://github.com/wrench-project/wrench.git && cd wrench && git checkout cb3befe95bf0f04052a8b37c37e0f8e1b0416428 && mkdir build && cd build && cmake .. && make -j4 && make install && cd .. && rm -rf wrench

#################################################
## WfCommons
#################################################

RUN apt-get install -y gfortran
RUN apt-get install -y libopenblas-dev

RUN git clone https://github.com/wfcommons/wfcommons.git && cd wfcommons && git checkout 29c69989fe5701bc07eb66c0077531f60e8a4414 && python3 -m pip install . && cd .. && rm -rf wfcommons

#################################################
# Workflow simulation calibrator
#################################################

# install stuff needed by DeepHyper
RUN apt-get install -y texlive
RUN apt-get install -y texlive-latex-extra
RUN apt-get install -y cm-super
RUN apt-get install -y dvipng

# Clone workflow-simulator-for-calibration and install the simulator and deephyper
RUN git clone https://github.com/wrench-project/workflow-simulator-for-calibration.git && cd workflow-simulator-for-calibration && git checkout main&& mkdir build && cd build && cmake .. && make -j4 && make install && cd ..

RUN cd workflow-simulator-for-calibration && python3 -m pip install -r calibration/requirements.txt && cd .. && rm -rf workflow-simulator-for-calibration



#################################################
# WRENCH's user
#################################################
RUN useradd -ms /bin/bash wrench
RUN adduser wrench sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER wrench
WORKDIR /home/wrench

# set user's environment variable
ENV CXX="g++" CC="gcc"
ENV LD_LIBRARY_PATH="/usr/local/lib"

