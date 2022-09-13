/**
 ** This is the main function for a WRENCH simulator of workflow
 ** executions, which takes in a number of calibration parameters.
 **/

#include <iostream>
#include <wrench-dev.h>

#include "Controller.h"
#include <boost/json.hpp>
#include <PlatformCreator.h>

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

    std::set<std::string> implemented_compute_service_schemes = {"all_bare_metal","batch_only", "htcondor_batch"};
    std::set<std::string> implemented_storage_service_schemes = {"submit_only","submit_and_slurm_head"};
    std::set<std::string> implemented_network_topology_schemes = {"one_link","two_links","many_links"};

    // Create and initialize simulation
    auto simulation = wrench::Simulation::createSimulation();
    simulation->init(&argc, argv);

    // Parse command-line arguments
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <json input file>" << std::endl;
        std::cerr << "       " << argv[0] << " --help" << std::endl;
        exit(1);
    }

    if (std::string(argv[1]) == "--help") {
        std::cerr << "Usage: " << argv[0] << " <json input file>" << std::endl;
        std::cerr << "  Implemented compute service schemes:\n";
        for (auto const &scheme : implemented_compute_service_schemes) {
            std::cerr << "    - " << scheme << "\n";
        }
        std::cerr << "  Implemented storage service schemes:\n";
        for (auto const &scheme : implemented_storage_service_schemes) {
            std::cerr << "    - " << scheme << "\n";
        }
        std::cerr << "  Implemented network topology schemes:\n";
        for (auto const &scheme : implemented_network_topology_schemes) {
            std::cerr << "    - " << scheme << "\n";
        }
        exit(0);
    }

    // Parse the JSON input file
    boost::json::object json_input;
    try {
        json_input = readJSONFromFile(argv[1]);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error while reading JSON file " << argv[1] << ": " << e.what() << "\n";
    }

    // Determine all the schemes
    std::string compute_service_scheme;
    std::string storage_service_scheme;
    std::string network_topology_scheme;
    try {
        compute_service_scheme = boost::json::value_to<std::string>(json_input["compute_service_scheme"]);
    } catch (std::exception &e) {
        std::cerr << "Error: Invalid or missing compute_service_scheme specification in JSON input (" << e.what() <<  ")\n";
        exit(1);
    }
    if (implemented_compute_service_schemes.find(compute_service_scheme) == implemented_compute_service_schemes.end()) {
        std::cerr << "Error: unknown or unimplemented compute service scheme " << compute_service_scheme << "\n";
    }
    try {
        storage_service_scheme = boost::json::value_to<std::string>(json_input["storage_service_scheme"]);
    } catch (std::exception &e) {
        std::cerr << "Error: Invalid or missing storage_service_scheme specification in JSON input (" << e.what() <<  ")\n";
        exit(1);
    }
    if (implemented_storage_service_schemes.find(storage_service_scheme) == implemented_storage_service_schemes.end()) {
        std::cerr << "Error: unknown or unimplemented storage service scheme " << storage_service_scheme << "\n";
    }
    try {
        network_topology_scheme = boost::json::value_to<std::string>(json_input["network_topology_scheme"]);
    } catch (std::exception &e) {
        std::cerr << "Error: Invalid or missing network_topology_scheme specification in JSON input (" << e.what() <<  ")\n";
        exit(1);
    }
    if (implemented_network_topology_schemes.find(network_topology_scheme) == implemented_network_topology_schemes.end()) {
        std::cerr << "Error: unknown or unimplemented network topology scheme " << network_topology_scheme << "\n";
    }

    // Instantiating the simulated platform
    try {
        PlatformCreator platform_creator(json_input);
        simulation->instantiatePlatform(platform_creator);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << "\n";
        exit(1);
    }

    // Create the workflow
    std::shared_ptr<wrench::Workflow> workflow;
    std::string workflow_file;
    try {
        std::string reference_flops;
        try {
            workflow_file = boost::json::value_to<std::string>(json_input["workflow"].as_object()["file"]);
            reference_flops = boost::json::value_to<std::string>(json_input["workflow"].as_object()["reference_flops"]);
        } catch (std::exception &e) {
            std::cerr << "Error: Invalid or missing workflow file or reference_flops specification in JSON input (" << e.what() <<  ")\n";
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
                // This next line will not compile with Boost 1.79 (works with Boost 1.76)
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

    // Gather all relevant hostnames and perform sanity checks
    std::string submit_node_hostname;
    std::string slurm_head_node_hostname;
    std::vector<std::string> slurm_compute_node_hostnames;
    for (const auto &h : simgrid::s4u::Engine::get_instance()->get_all_hosts()) {
        if (std::string(h->get_property("type")) == "submit") {
            if (not submit_node_hostname.empty()) {
                std::cerr << "Error: More than one host of type 'submit' in the platform description\n";
                exit(1);
            } else {
                submit_node_hostname = h->get_cname();
            }
        }
        if (std::string(h->get_property("type")) == "slurm_head") {
            if (not submit_node_hostname.empty()) {
                std::cerr << "Error: More than one host of type 'slurm_head' in the platform description\n";
                exit(1);
            } else {
                slurm_head_node_hostname = h->get_cname();
            }
        }
        if (std::string(h->get_property("type")) == "compute") {
                slurm_compute_node_hostnames.emplace_back(h->get_cname());
        }
    }
    if (submit_node_hostname.empty()) {
        std::cerr << "Error: There should be a host of type 'submit' in the platform description\n";
        exit(1);
    }
    if (slurm_head_node_hostname.empty()) {
        std::cerr << "Error: There should be a host of type 'slurm_head' in the platform description\n";
        exit(1);
    }
    if (slurm_compute_node_hostnames.empty()) {
        std::cerr << "Error: There should be at least one host of type 'slurm_compute' in the platform description\n";
        exit(1);
    }

    // Create relevant storage services

    // There is always a storage service on the submit_node
    auto submit_node_storage_service =
            simulation->add(new wrench::SimpleStorageService(
                    submit_node_hostname,
                    {{"/"}},
                    storage_service_property_list,
                    storage_service_messagepayload_list));

    // There may be a storage service on the slurm head node
    std::shared_ptr<wrench::StorageService> slurm_head_node_storage_service = nullptr;
    if (storage_service_scheme == "submit_and_slurm_head") {
        slurm_head_node_storage_service =
                simulation->add(new wrench::SimpleStorageService(
                        slurm_head_node_hostname,
                        {{"/"}},
                        storage_service_property_list,
                        storage_service_messagepayload_list));
    }

    // Create relevant compute services

    std::set<std::shared_ptr<wrench::ComputeService>> compute_services;

    if (compute_service_scheme == "all_bare_metal") {
        // Create one bare-metal service on all compute nodes
        for (auto const &host : slurm_compute_node_hostnames) {
            compute_services.insert(simulation->add(
                    new wrench::BareMetalComputeService(
                            host,
                            {host},
                            "",
                            compute_service_property_list,
                            compute_service_messagepayload_list)));
        }

    } else if (compute_service_scheme == "batch_only") {
        // Create a batch compute service that manages all compute nodes
        compute_services.insert(simulation->add(
                new wrench::BatchComputeService(
                        slurm_head_node_hostname,
                        slurm_compute_node_hostnames,
                        "",
                        compute_service_property_list,
                        compute_service_messagepayload_list)));

    } else if (compute_service_scheme == "htcondor_batch") {
        // Create a batch compute service that manages all compute nodes
        auto batch = simulation->add(
                new wrench::BatchComputeService(
                        slurm_head_node_hostname,
                        slurm_compute_node_hostnames,
                        "",
                        compute_service_property_list,
                        compute_service_messagepayload_list));
        // Create a top-level HTCondor compute service
        // TODO: EXPOSE THE PROPERTIES IN THE JSON
        compute_services.insert(simulation->add(
                new wrench::HTCondorComputeService(
                        submit_node_hostname,
                        {batch},
                        {{wrench::HTCondorComputeServiceProperty::NEGOTIATOR_OVERHEAD, "1.0"},
                         {wrench::HTCondorComputeServiceProperty::GRID_PRE_EXECUTION_DELAY, "10.0"},
                         {wrench::HTCondorComputeServiceProperty::GRID_POST_EXECUTION_DELAY, "10.0"},
                         {wrench::HTCondorComputeServiceProperty::NON_GRID_PRE_EXECUTION_DELAY, "5.0"},
                         {wrench::HTCondorComputeServiceProperty::NON_GRID_POST_EXECUTION_DELAY, "5.0"}},
                        {})));
    }

    // Instantiate a Controller on the submit_host
    double scheduling_overhead;
    try {
        scheduling_overhead = boost::json::value_to<double>(json_input["scheduling_overhead"]);
    } catch (std::exception &e) {
        std::cerr << "Error: Invalid or missing scheduling_overhead specification in JSON input (" << e.what() <<  ")\n";
        exit(1);
    }

    simulation->add(
            new wrench::Controller(workflow,
                                   compute_service_scheme,
                                   storage_service_scheme,
                                   compute_services,
                                   submit_node_storage_service,
                                   slurm_head_node_storage_service,
                                   scheduling_overhead,
                                   submit_node_hostname));

    // Create each file ab-initio on the storage service (no file registry service)
    for (auto const &f: workflow->getInputFiles()) {
        submit_node_storage_service->createFile(f);
    }

    // Launch the simulation
    try {
        simulation->launch();
    } catch (std::runtime_error &e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 0;
    }

    // Retrieve the observed execution time of the workflow on the actual platform
    boost::json::object json_workflow;
    try {
        json_workflow = readJSONFromFile(workflow_file);
    } catch (std::invalid_argument &e) {
        std::cerr << "Error while reading JSON file " << workflow_file << ": " << e.what() << "\n";
    }
    
    double observed_makespan = boost::json::value_to<double>(json_workflow["workflow"].as_object()["makespan"]);
    // Get the makespan of the simulated workflow
    double simu_makespan = workflow->getCompletionDate();
    double err = observed_makespan - simu_makespan;

    std::cout << simu_makespan << ":" << observed_makespan << ":" << std::fabs(err / simu_makespan) << std::endl;

    return 0;
}
