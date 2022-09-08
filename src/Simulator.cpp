/**
 ** This is the main function for a WRENCH simulator of workflow
 ** executions, which takes in a number of calibration parameters.
 **/

#define GFLOP (1000.0 * 1000.0 * 1000.0)
#define MBYTE (1000.0 * 1000.0)
#define GBYTE (1000.0 * 1000.0 * 1000.0)

#include <iostream>
#include <wrench-dev.h>

#include "Controller.h"
#include <boost/json.hpp>

/**
 * @brief Helper function to read a JSON object from a file
 * @param filepath: the file path
 * @return a boost::json::object object
 */
boost::json::object readJSONFromFile(const std::string& filepath) {
    FILE *file = fopen(filepath.c_str(), "r");
    if (not file) {
        throw std::invalid_argument("Cannot read JSON file " + filepath);
    }

    boost::json::stream_parser p;
    boost::json::error_code ec;
    p.reset();
    while (true) {
        try {
            char buf[1024];
            auto nread = fread(buf, sizeof(char), 1024, file);
            if (nread == 0) {
                break;
            }
            p.write(buf, nread, ec);
        } catch (std::exception &e) {
            throw std::invalid_argument("Error while reading JSON file " + filepath + ": " + std::string(e.what()));
        }
    }

    p.finish(ec);
    if (ec) {
        throw std::invalid_argument("Error while reading JSON file " + filepath + ": " + ec.message());
    }
    return p.release().as_object();
}

/**
 * @brief The Simulator's main function
 *
 * @param argc: argument count
 * @param argv: argument array
 * @return 0 on success, non-zero otherwise
 */
int main(int argc, char **argv) {

    // Create and initialize simulation
    auto simulation = wrench::Simulation::createSimulation();
    simulation->init(&argc, argv);

    // Parse command-line arguments
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <json input file>" << std::endl;
        exit(1);
    }

    // Parse the JSON input file
    boost::json::object json_input;
    try {
        json_input = readJSONFromFile(argv[1]);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error while reading JSON file " << argv[1] << ": " << e.what() << "\n";
    }

    // Get all the top-level information from the JSON input into
    std::unordered_map<std::string, std::string> top_level_parameters;
    std::vector<std::string> parameter_keys = {
            "platform",
            "workflow",
            "reference_flops",
    };

    for (auto const &key : parameter_keys) {
        if (json_input.find(key) == json_input.end()) {
            std::cerr << "Error: cannot find top-level item with key '" << key << "' in JSON input file\n";
            exit(1);
        }
        top_level_parameters[key] = boost::json::value_to<std::string>(json_input[key]);
    }

    // Instantiating the simulated platform
    try {
        simulation->instantiatePlatform(top_level_parameters["platform"]);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << "\n";
        exit(1);
    }

    // Create the workflow
    std::shared_ptr<wrench::Workflow> workflow;
    try {
        workflow = wrench::WfCommonsWorkflowParser::createWorkflowFromJSON(
                top_level_parameters["workflow"],
                top_level_parameters["reference_flops"]);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << "\n";

    }

    // Instantiate a compute service on each "compute" node along with its
    // local storage service
    std::vector<
            std::pair<std::shared_ptr<wrench::ComputeService>,
                    std::shared_ptr<wrench::StorageService>>> compute_node_services;
    std::shared_ptr<wrench::StorageService> submit_node_storage_service;
    std::string submit_hostname;

    for (const auto &h : simgrid::s4u::Engine::get_instance()->get_all_hosts()) {
        if (std::string(h->get_property("type")) == "compute") {
            auto compute_service = simulation->add(new wrench::BareMetalComputeService(
                    h->get_cname(),
                    {h->get_cname()},
                    "/",
                    {},
                    {}));
            auto storage_service = simulation->add(new wrench::SimpleStorageService(
                    h->get_cname(),
                    {{"/"}},
                    {
                            {wrench::SimpleStorageServiceProperty::BUFFER_SIZE,
                                    parameters["storage_service_buffer_size"]},
                            {wrench::SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS,
                                    boost::json::value_to<std::string>(json_input["max_num_concurrent_data_connections"])}
                    },
                    {}));
            compute_node_services.emplace_back(compute_service, storage_service);

        } else if (std::string(h->get_property("type")) == "submit") {
            if (submit_node_storage_service) {
                throw std::invalid_argument("There should be a single host of type 'submit' in the platform");
            }
            submit_hostname = h->get_cname();
            submit_node_storage_service = simulation->add(new wrench::SimpleStorageService(
                    h->get_cname(),
                    {{"/"}},
                    {
                            {wrench::SimpleStorageServiceProperty::BUFFER_SIZE,
                                    boost::json::value_to<std::string>(json_input["storage_service_buffer_size"])},
                            {wrench::SimpleStorageServiceProperty::MAX_NUM_CONCURRENT_DATA_CONNECTIONS,
                                    boost::json::value_to<std::string>(json_input["max_num_concurrent_data_connections"])}
                    },
                    {}));
        }
    }

    // Instantiate a Controller on the submit_host
    simulation->add(
            new wrench::Controller(workflow, compute_node_services, submit_node_storage_service, submit_hostname));

///* Instantiate a file registry service */
//auto file_registry_service = new wrench::FileRegistryService("UserHost");
//simulation->add(file_registry_service);

    // Stage input files on the storage service
    for (auto const &f: workflow->getInputFiles()) {
        simulation->stageFile(f, submit_node_storage_service);
    }

    // Launch the simulation
    simulation->launch();

    return 0;
}
