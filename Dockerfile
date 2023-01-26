FROM amd64/ubuntu:jammy

LABEL org.opencontainers.image.authors="henric@hawaii.edu"

# add repositories
RUN apt-get update

# set timezone
RUN echo "America/Los_Angeles" > /etc/timezone && export DEBIAN_FRONTEND=noninteractive && apt-get install -y tzdata

# build environment
RUN apt-get -y install pkg-config git cmake cmake-data libboost-all-dev wget sudo curl

# install doxygen and sphinx
#RUN apt-get install -y doxygen
#RUN apt-get install -y python3 
#RUN apt-get install -y python3-pip
#RUN pip3 install --upgrade pip
#RUN pip3 install Sphinx sphinx-rtd-theme breathe recommonmark

# install compiler
RUN apt-get -y install gcc g++

# install lvoc
#RUN apt-get -y install lcov


#################################################
# WRENCH's dependencies
#################################################

# set root's environment variable
ENV CXX="g++" CC="gcc"
WORKDIR /tmp

# install Boost 1.80
RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.80.0/source/boost_1_80_0.tar.gz && tar -xvf boost_1_80_0.tar.gz && cd boost_1_80_0 && ./bootstrap.sh && ./b2 && ./b2 install && cd .. && rm -rf boost_1_80_0

# install SimGrid master
RUN git clone https://framagit.org/simgrid/simgrid.git && cd simgrid && git checkout 245c3edbc5f324cd5a0f0cfb862b5c5f55c5a4d2 && mkdir build && cd build && cmake .. && make -j12 && sudo make install && cd ../.. && rm -rf simgrid

# install json for modern c++
RUN wget https://github.com/nlohmann/json/archive/refs/tags/v3.10.5.tar.gz && tar -xf v3.10.5.tar.gz && cd json-3.10.5 && cmake . && make -j4 && make install && cd .. && rm -rf v3.10.5* json-3.10.5

# install WRENCH
RUN git clone https://github.com/wrench-project/wrench.git && cd wrench && git checkout 1c77d7c0070262cb5356e169e42c009b46369155 && mkdir build && cd build && cmake .. && make -j4 && make install && cd .. && rm -rf wrench

# install Calibration simulator
RUN git clone https://github.com/wrench-project/workflow-simulator-for-calibration.git && cd workflow-simulator-for-calibration && mkdir build && cd build && cmake .. && make -j4 && make install && cd .. && rm -rf workflow-simulator-for-calibration

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
