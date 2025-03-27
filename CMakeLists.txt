
cmake_minimum_required(VERSION 3.12)
message(STATUS "Cmake version ${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION}.${CMAKE_PATCH_VERSION}")

project(workflow-simulator-for-calibration CXX)

# Disable annoying warnings
add_definitions("-DBOOST_ALLOW_DEPRECATED_HEADERS")
#add_definitions("-DBOOST_BIND_GLOBAL_PLACEHOLDERS")

add_definitions("-Wall -Wno-unused-variable -Wno-unused-private-field")

set(CMAKE_CXX_STANDARD 17)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/CMakeModules/")

# Find WRENCH, SimGrid, and Boost
find_package(WRENCH REQUIRED)
find_package(SimGrid REQUIRED)
find_package(FSMod REQUIRED)


if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()
find_package(Boost REQUIRED)
find_package(Boost COMPONENTS json REQUIRED)

# include directories
include_directories(include/ /usr/local/include/ /opt/local/include/ ${WRENCH_INCLUDE_DIR} ${SimGrid_INCLUDE_DIR} ${Boost_INCLUDE_DIR})

# source files
set(SOURCE_FILES
        include/UnitParser.h
        src/UnitParser.cpp
        include/PlatformCreator.h
        src/PlatformCreator.cpp
        include/Controller.h
        src/Controller.cpp
        src/Simulator.cpp
        )

# generating the executable
add_executable(workflow-simulator-for-calibration ${SOURCE_FILES})

# Specify libraries to link
if (ENABLE_BATSCHED)
    target_link_libraries(workflow-simulator-for-calibration
            ${WRENCH_LIBRARY}
            ${SimGrid_LIBRARY}
            ${FSMOD_LIBRARY}
            ${Boost_LIBRARIES}
            ${WRENCH_WFCOMMONS_WORKFLOW_PARSER_LIBRARY}
            -lzmq)
else()
    target_link_libraries(workflow-simulator-for-calibration
            ${WRENCH_LIBRARY}
            ${SimGrid_LIBRARY}
            ${FSMOD_LIBRARY}
            ${Boost_LIBRARIES}
            ${WRENCH_WFCOMMONS_WORKFLOW_PARSER_LIBRARY}
            )
endif()

install(TARGETS workflow-simulator-for-calibration DESTINATION bin)
