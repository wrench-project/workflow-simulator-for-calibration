#ifndef WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H
#define WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H

#include <boost/json.hpp>

class PlatformCreator {

public:
    PlatformCreator(boost::json::object &json_spec, unsigned long num_compute_hosts);

    void operator()() {
        this->create_platform();
    }

private:
    unsigned long num_compute_hosts;
    boost::json::object json_spec;
    void create_platform();

};


#endif //WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H
