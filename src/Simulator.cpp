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



    // Instantiating the simulated platform
    try {
        std::string platform_file;
        try {
            platform_file = boost::json::value_to<std::string>(json_input["platform"].as_object()["file"]);
        } catch (std::exception &e) {
            std::cerr << "Error: Invalid platform file specification in JSON input (" << e.what() <<  ")\n";
            exit(1);
        }
        simulation->instantiatePlatform(platform_file);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << "\n";
        exit(1);
    }

    // Create the workflow
    std::shared_ptr<wrench::Workflow> workflow;
    try {
        std::string workflow_file;
        std::string reference_flops;
        try {
            workflow_file = boost::json::value_to<std::string>(json_input["workflow"].as_object()["file"]);
            reference_flops = boost::json::value_to<std::string>(json_input["workflow"].as_object()["reference_flops"]);
        } catch (std::exception &e) {
            std::cerr << "Error: Invalid workflow file or reference_flops specification in JSON input (" << e.what() <<  ")\n";
            exit(1);
        }
        workflow = wrench::WfCommonsWorkflowParser::createWorkflowFromJSON(
                workflow_file,
                reference_flops);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << "\n";

    }


    // Create Property Lists and Payload Lists for storage services
    wrench::WRENCH_PROPERTY_COLLECTION_TYPE storage_service_property_list;
    wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE storage_service_messagepayload_list;

    if (json_input.find("storage_service_properties") != json_input.end()) {
        for (const auto &prop : json_input["storage_service_properties"].as_object()) {
            if (prop.value().as_object().size() != 1)  {
                std::cerr << "Error: Invalid property specification in JSON input file for " << prop.key() << "\n";
                exit(1);
            }
            for (const auto &spec : prop.value().as_object()) {
                auto property_name = prop.key().to_string() + "::" + spec.key().to_string();
                auto property = wrench::StorageServiceProperty::translateString(property_name);
                std::string property_value = boost::json::value_to<std::string>(spec.value());
                storage_service_property_list[property] = property_value;
            }
        }
    }
    if (json_input.find("storage_service_payloads") != json_input.end()) {
        for (const auto &pl : json_input["storage_service_payloads"].as_object()) {
            if (pl.value().as_object().size() != 1)  {
                std::cerr << "Error: Invalid payload specification in JSON input file for " << pl.key() << "\n";
                exit(1);
            }
            for (const auto &spec : pl.value().as_object()) {
                auto payload_name = pl.key().to_string() + "::" + spec.key().to_string();
                auto payload = wrench::StorageServiceMessagePayload::translateString(payload_name);
                double payload_value = spec.value().as_double();
                storage_service_messagepayload_list[payload] = payload_value;
            }
        }
    }

    // Create Property Lists and Payload Lists for compute services
    wrench::WRENCH_PROPERTY_COLLECTION_TYPE compute_service_property_list;
    wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE compute_service_messagepayload_list;

    if (json_input.find("compute_service_properties") != json_input.end()) {
        for (const auto &prop : json_input["compute_service_properties"].as_object()) {
            if (prop.value().as_object().size() != 1)  {
                std::cerr << "Error: Invalid property specification in JSON input file for " << prop.key() << "\n";
                exit(1);
            }
            for (const auto &spec : prop.value().as_object()) {
                auto property_name = prop.key().to_string() + "::" + spec.key().to_string();
                auto property = wrench::ComputeServiceProperty::translateString(property_name);
                std::string property_value = boost::json::value_to<std::string>(spec.value());
                compute_service_property_list[property] = property_value;
            }
        }
    }
    if (json_input.find("compute_service_payloads") != json_input.end()) {
        for (const auto &pl : json_input["compute_service_payloads"].as_object()) {
            if (pl.value().as_object().size() != 1)  {
                std::cerr << "Error: Invalid payload specification in JSON input file for " << pl.key() << "\n";
                exit(1);
            }
            for (const auto &spec : pl.value().as_object()) {
                auto payload_name = pl.key().to_string() + "::" + spec.key().to_string();
                auto payload = wrench::ComputeServiceMessagePayload::translateString(payload_name);
                double payload_value = spec.value().as_double();
                compute_service_messagepayload_list[payload] = payload_value;
            }
        }
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
                    "",
                    compute_service_property_list,
                    compute_service_messagepayload_list));
            auto storage_service = simulation->add(new wrench::SimpleStorageService(
                    h->get_cname(),
                    {{"/"}},
                    storage_service_property_list,
                    storage_service_messagepayload_list));
            compute_node_services.emplace_back(compute_service, storage_service);

        } else if (std::string(h->get_property("type")) == "submit") {
            if (submit_node_storage_service) {
                throw std::invalid_argument("There should be a single host of type 'submit' in the platform");
            }
            submit_hostname = h->get_cname();
            submit_node_storage_service = simulation->add(new wrench::SimpleStorageService(
                    h->get_cname(),
                    {{"/"}},
                    storage_service_property_list,
                    storage_service_messagepayload_list));
        }
    }

    // Instantiate a Controller on the submit_host
    simulation->add(
            new wrench::Controller(workflow, compute_node_services, submit_node_storage_service, submit_hostname));

    // Create each file ab-initio on the storage service
    for (auto const &f: workflow->getInputFiles()) {
        submit_node_storage_service->createFile(f);
    }

    // Launch the simulation
    simulation->launch();

    return 0;
}
