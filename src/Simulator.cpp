/**
 ** This is the main function for a WRENCH simulator of workflow
 ** executions, which takes in a number of calibration parameters.
 **/

#include <iostream>
#include <wrench-dev.h>

#include "UnitParser.h"
#include "Controller.h"
#include <boost/json.hpp>
#include <PlatformCreator.h>


/**
 * All implemented schemes as ugly globals
 */
std::set<std::string> implemented_compute_service_schemes = {"all_bare_metal","batch_only", "htcondor_batch"};
std::set<std::string> implemented_storage_service_schemes = {"submit_only","submit_and_slurm_head"};
std::set<std::string> implemented_network_topology_schemes = {"one_link","two_links","many_links"};



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

void display_help(char *executable_name) {
    std::cerr << "Usage: " << executable_name << " <json input file>" << std::endl;
    std::cerr << "  Implemented compute service schemes:\n";
    for (auto const &scheme : implemented_compute_service_schemes) {
        std::cerr << "    - " << scheme << std::endl;
    }
    std::cerr << "  Implemented storage service schemes:\n";
    for (auto const &scheme : implemented_storage_service_schemes) {
        std::cerr << "    - " << scheme << std::endl;
    }
    std::cerr << "  Implemented network topology schemes:\n";
    for (auto const &scheme : implemented_network_topology_schemes) {
        std::cerr << "    - " << scheme << std::endl;
    }
}

void determine_all_schemes(boost::json::object &json_input,
                           std::string &compute_service_scheme,
                           std::string &storage_service_scheme,
                           std::string &network_topology_scheme) {
    try {
        compute_service_scheme = boost::json::value_to<std::string>(json_input["compute_service_scheme"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing compute_service_scheme specification in JSON input (" + std::string(e.what()) + ")");
        exit(1);
    }
    if (implemented_compute_service_schemes.find(compute_service_scheme) == implemented_compute_service_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented compute service scheme " + compute_service_scheme);
    }
    try {
        storage_service_scheme = boost::json::value_to<std::string>(json_input["storage_service_scheme"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing storage_service_scheme specification in JSON input (" + std::string(e.what()) +")");
        exit(1);
    }
    if (implemented_storage_service_schemes.find(storage_service_scheme) == implemented_storage_service_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented storage service scheme " + storage_service_scheme + ")");
    }
    try {
        network_topology_scheme = boost::json::value_to<std::string>(json_input["network_topology_scheme"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing network_topology_scheme specification in JSON input (" + std::string(e.what()) + ")");
        exit(1);
    }
    if (implemented_network_topology_schemes.find(network_topology_scheme) == implemented_network_topology_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented network topology scheme " + network_topology_scheme);
    }
}

std::shared_ptr<wrench::Workflow> create_workflow(boost::json::object &json_input, double *observed_real_makespan) {
    std::string workflow_file;
    std::string reference_flops;
    try {
        workflow_file = boost::json::value_to<std::string>(json_input["workflow"].as_object()["file"]);
        reference_flops = boost::json::value_to<std::string>(json_input["workflow"].as_object()["reference_flops"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing workflow file or reference_flops specification in JSON input (" +
                                    std::string(e.what()) + ")");
    }

    // Parse the workflow's JSON file to find the real observed makespan
    boost::json::object json_workflow;
    try {
        json_workflow = readJSONFromFile(workflow_file);
        *observed_real_makespan = boost::json::value_to<double>(json_workflow["workflow"].as_object()["makespan"]);
    } catch (std::exception &e) {
        throw;
    }

    return wrench::WfCommonsWorkflowParser::createWorkflowFromJSON(workflow_file, reference_flops);
}



void process_hostnames(std::string &submit_host_name, std::string &slurm_head_host_name,
                       std::vector<std::string> &compute_host_names) {
    // Gather all relevant hostnames and perform sanity checks
    for (const auto &h : simgrid::s4u::Engine::get_instance()->get_all_hosts()) {
        if (std::string(h->get_property("type")) == "submit") {
            if (not submit_host_name.empty()) {
                throw std::invalid_argument("More than one host of type 'submit' in the platform description");
            } else {
                submit_host_name = h->get_cname();
            }
        }
        if (std::string(h->get_property("type")) == "slurm_head") {
            if (not slurm_head_host_name.empty()) {
                throw std::invalid_argument("More than one host of type 'slurm_head' in the platform description");
            } else {
                slurm_head_host_name = h->get_cname();
            }
        }
        if (std::string(h->get_property("type")) == "compute") {
            compute_host_names.emplace_back(h->get_cname());
        }
    }
    if (compute_host_names.empty()) {
        throw std::invalid_argument("There should be a host of type 'submit' in the platform description");
    }
    if (slurm_head_host_name.empty()) {
        throw std::invalid_argument("There should be a host of type 'slurm_head' in the platform description");
    }
    if (compute_host_names.empty()) {
        throw std::invalid_argument("There should be at least one host of type 'slurm_compute' in the platform description");
    }

}

wrench::WRENCH_PROPERTY_COLLECTION_TYPE get_properties(boost::json::object &json_input,
                                                       std::string scheme_category,
                                                       std::string scheme,
                                                       std::string properties_key) {

    wrench::WRENCH_PROPERTY_COLLECTION_TYPE property_list;
    auto specs = json_input[scheme_category].as_object()[scheme].as_object();

    if (specs.contains(properties_key)) {
        for (const auto &prop : specs[properties_key].as_object()) {
            if (prop.value().as_object().size() != 1) {
                throw std::invalid_argument("Error: Invalid " + properties_key + " specification in JSON input file for " +
                                            prop.key().to_string());
            }
            for (const auto &spec : prop.value().as_object()) {
                // This next line will not compile with Boost 1.79 (works with Boost 1.76)
                auto property_name = prop.key().to_string() + "::" + spec.key().to_string();
                auto property = wrench::ServiceProperty::translateString(property_name);
                std::string property_value = boost::json::value_to<std::string>(spec.value());
                property_list[property] = property_value;
            }
        }
    }
    return property_list;
}

wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE get_payloads(boost::json::object &json_input,
                                                           std::string scheme_category,
                                                           std::string scheme,
                                                           std::string payloads_key) {

    wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE  payload_list;
    auto specs = json_input[scheme_category].as_object()[scheme].as_object();

    if (specs.contains(payloads_key)) {
        for (const auto &pl : specs[payloads_key].as_object()) {
            if (pl.value().as_object().size() != 1) {
                throw std::invalid_argument("Error: Invalid " + payloads_key +
                                            " specification in JSON input file for " +
                                            pl.key().to_string());
            }
            for (const auto &spec : pl.value().as_object()) {
                // This next line will not compile with Boost 1.79 (works with Boost 1.76)
                auto payload_name = spec.key().to_string() + "::" + spec.key().to_string();
                auto payload = wrench::ServiceMessagePayload::translateString(payload_name);
                double payload_value = spec.value().as_double();
                payload_list[payload] = payload_value;
            }
        }
    }
    return payload_list;
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

    // Check command-line arguments
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <json input file>" << std::endl;
        std::cerr << "       " << argv[0] << " --help" << std::endl;
        exit(1);
    }

    // Display help message and exit is --help is the argument
    if (std::string(argv[1]) == "--help") {
        display_help(argv[0]);
        exit(0);
    }

    // Process necessary input
    boost::json::object json_input;
    std::string compute_service_scheme, storage_service_scheme, network_topology_scheme;
    std::shared_ptr<wrench::Workflow> workflow;
    double observed_real_makespan;
    std::string submit_host_name;
    std::string slurm_head_host_name;
    std::vector<std::string> compute_host_names;
    try {
        // Read JSON input
        json_input = readJSONFromFile(argv[1]);
        // Determine schemes in use
        determine_all_schemes(json_input, compute_service_scheme, storage_service_scheme, network_topology_scheme);
        // Create the platform
        PlatformCreator platform_creator(json_input);
        simulation->instantiatePlatform(platform_creator);
        // Create the workflow for the WRENCH simulation
        workflow = create_workflow(json_input, &observed_real_makespan);
        // Gather all relevant hostnames and perform sanity checks
        process_hostnames(submit_host_name, slurm_head_host_name, compute_host_names);

    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << std::endl;
        exit(1);
    }

    // Create Property Lists and Payload Lists for storage services
//    wrench::WRENCH_PROPERTY_COLLECTION_TYPE storage_service_property_list;
//    wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE storage_service_messagepayload_list;
//
//    wrench::WRENCH_PROPERTY_COLLECTION_TYPE storage_service_property_listget_storage_service_properties(json_input, storage_service_scheme);

//
//    if (json_input.find("storage_service_payloads") != json_input.end()) {
//        for (const auto &pl : json_input["storage_service_payloads"].as_object()) {
//            if (pl.value().as_object().size() != 1)  {
//                std::cerr << "Error: Invalid payload specification in JSON input file for " << pl.key() << std::endl;
//                exit(1);
//            }
//            for (const auto &spec : pl.value().as_object()) {
//                auto payload_name = pl.key().to_string() + "::" + spec.key().to_string();
//                auto payload = wrench::StorageServiceMessagePayload::translateString(payload_name);
//                double payload_value = spec.value().as_double();
//                storage_service_messagepayload_list[payload] = payload_value;
//            }
//        }
//    }
//
//    // Create Property Lists and Payload Lists for compute services
//    wrench::WRENCH_PROPERTY_COLLECTION_TYPE compute_service_property_list;
//    wrench::WRENCH_MESSAGE_PAYLOADCOLLECTION_TYPE compute_service_messagepayload_list;
//
//    if (json_input.find("compute_service_properties") != json_input.end()) {
//        for (const auto &prop : json_input["compute_service_properties"].as_object()) {
//            if (prop.value().as_object().size() != 1)  {
//                std::cerr << "Error: Invalid property specification in JSON input file for " << prop.key() << std::endl;
//                exit(1);
//            }
//            for (const auto &spec : prop.value().as_object()) {
//                auto property_name = prop.key().to_string() + "::" + spec.key().to_string();
//                auto property = wrench::ComputeServiceProperty::translateString(property_name);
//                std::string property_value = boost::json::value_to<std::string>(spec.value());
//                compute_service_property_list[property] = property_value;
//            }
//        }
//    }
//    if (json_input.find("compute_service_payloads") != json_input.end()) {
//        for (const auto &pl : json_input["compute_service_payloads"].as_object()) {
//            if (pl.value().as_object().size() != 1)  {
//                std::cerr << "Error: Invalid payload specification in JSON input file for " << pl.key() << std::endl;
//                exit(1);
//            }
//            for (const auto &spec : pl.value().as_object()) {
//                auto payload_name = pl.key().to_string() + "::" + spec.key().to_string();
//                auto payload = wrench::ComputeServiceMessagePayload::translateString(payload_name);
//                double payload_value = spec.value().as_double();
//                compute_service_messagepayload_list[payload] = payload_value;
//            }
//        }
//    }


    // Create relevant storage services

    // There is always a storage service on the submit_node
    auto submit_node_storage_service =
            simulation->add(new wrench::SimpleStorageService(
                    submit_host_name,
                    {{"/"}},
                    get_properties(json_input,
                                   "storage_service_scheme_parameters",
                                   storage_service_scheme,
                                   "submit_properties"),
                    get_payloads(json_input,
                                 "storage_service_scheme_parameters",
                                 storage_service_scheme,
                                 "submit_payloads")));

    for (auto const &p:     submit_node_storage_service->getPropertyList()) {
        std::cerr << p.first << " " << wrench::ServiceProperty::translatePropertyType(p.first) << " " << p.second << "\n";
    }

    for (auto const &p: submit_node_storage_service->getMessagePayloadList()) {
        std::cerr << p.first << " " << wrench::ServiceMessagePayload::translatePayloadType(p.first) << " " << p.second << "\n";
    }

#if 0

    // There may be a storage service on the slurm head node
    std::shared_ptr<wrench::StorageService> slurm_head_node_storage_service = nullptr;
    if (storage_service_scheme == "submit_and_slurm_head") {
        slurm_head_node_storage_service =
                simulation->add(new wrench::SimpleStorageService(
                        slurm_head_node_hostname,
                        {{"/"}},
                        storage_service_property_list,
                        storage_service_messagepayload_list)));
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
        scheduling_overhead = UnitParser::parse_time(boost::json::value_to<std::string>(json_input["scheduling_overhead"]));
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

#endif

    // Launch the simulation
    try {
        simulation->launch();
    } catch (std::runtime_error &e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 0;
    }

    double simulated_makespan = workflow->getCompletionDate();
    double err = std::fabs(observed_real_makespan - simulated_makespan) / simulated_makespan;

    std::cout << simulated_makespan << ":" << observed_real_makespan << ":" << err << std::endl;

    return 0;
}
