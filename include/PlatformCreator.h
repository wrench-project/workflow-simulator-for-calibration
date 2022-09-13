#ifndef WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H
#define WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H

#include <boost/json.hpp>

class PlatformCreator {

public:
    PlatformCreator(boost::json::object &json_spec);

    void operator()() {
        this->create_platform();
    }

private:
    boost::json::object json_spec;
    void create_platform();

};


#endif //WORKFLOW_SIMULATOR_FOR_CALIBRATION_PLATFORMCREATOR_H
