/**
 ** This is the main function for a WRENCH simulator of workflow
 ** executions, which takes in a number of calibration parameters.
 **/

#include <iostream>
#include <wrench-dev.h>

#include "UnitParser.h"
#include "Controller.h"
#include <boost/json.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <PlatformCreator.h>

#define NETWORK_TIMEOUT 100000000.0

/**
 * All implemented schemes as ugly globals
 */
std::set<std::string> implemented_compute_service_schemes = {"all_bare_metal", "htcondor_bare_metal"};
std::set<std::string> implemented_storage_service_schemes = {"submit_only","submit_and_compute_hosts"};
std::set<std::string> implemented_network_topology_schemes = {"one_link","one_and_then_many_links","many_links"};



/**
 * @brief Helper function to read a JSON object from a file
 * @param filepath: the file path
 * @return a boost::json::object object
 */
boost::json::object readJSONFromFile(const std::string& filepath) {

    // Open the file using ifstream
    ifstream file(filepath);

    // Check if the file was opened successfully
    if (!file.is_open()) {
	std::cerr << "Failed to open file: " << filepath << endl;
        exit(1);
    }

    // Read the whole file into a string
    std::string json_string((istreambuf_iterator<char>(file)),
                       istreambuf_iterator<char>());
    file.close();

    // Parse string into an object

    auto json_object = boost::json::parse(json_string).as_object();
    return json_object;
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
    }
    if (implemented_compute_service_schemes.find(compute_service_scheme) == implemented_compute_service_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented compute service scheme " + compute_service_scheme);
    }
    try {
        storage_service_scheme = boost::json::value_to<std::string>(json_input["storage_service_scheme"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing storage_service_scheme specification in JSON input (" + std::string(e.what()) +")");
    }
    if (implemented_storage_service_schemes.find(storage_service_scheme) == implemented_storage_service_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented storage service scheme " + storage_service_scheme + ")");
    }
    try {
        network_topology_scheme = boost::json::value_to<std::string>(json_input["network_topology_scheme"]);
    } catch (std::exception &e) {
        throw std::invalid_argument("Invalid or missing network_topology_scheme specification in JSON input (" + std::string(e.what()) + ")");
    }
    if (implemented_network_topology_schemes.find(network_topology_scheme) == implemented_network_topology_schemes.end()) {
        throw std::invalid_argument("unknown or unimplemented network topology scheme " + network_topology_scheme);
    }
}



std::shared_ptr<wrench::Workflow> create_workflow(boost::json::object &json_input,
                                                  double *observed_real_makespan,
                                                  unsigned long *num_compute_hosts) {
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
        *observed_real_makespan = boost::json::value_to<double>(
                json_workflow["workflow"].as_object()["execution"].as_object()["makespanInSeconds"]);
        *num_compute_hosts = json_workflow["workflow"].as_object()["execution"].as_object()["machines"].as_array().size();
    } catch (std::exception &e) {
        throw;
    }

    return wrench::WfCommonsWorkflowParser::createWorkflowFromJSON(workflow_file, reference_flops);
}



void process_hostnames(std::string &submit_host_name,
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
        if (std::string(h->get_property("type")) == "compute") {
            compute_host_names.emplace_back(h->get_cname());
        }
    }
    if (compute_host_names.empty()) {
        throw std::invalid_argument("There should be a host of type 'submit' in the platform description");
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
#if (BOOST_VERSION >= 108000)
            auto property = wrench::ServiceProperty::translateString(prop.key());
#else
            auto property = wrench::ServiceProperty::translateString(prop.key().to_string());
#endif
            std::string property_value = boost::json::value_to<std::string>(prop.value());
            property_list[property] = property_value;
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
#if (BOOST_VERSION >= 108000)
            auto payload = wrench::ServiceMessagePayload::translateString(pl.key());
#else

            auto payload = wrench::ServiceMessagePayload::translateString(pl.key().to_string());
#endif
            double payload_value =  std::strtod(boost::json::value_to<std::string>(pl.value()).c_str(), nullptr);
            payload_list[payload] = payload_value;
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
    if (argc != 2 and argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <JSON input file> [JSON workflow file]" << std::endl;
        std::cerr << "          (if JSON workflow file is provided, it overrides the workflow file specified in the JSON input file" << std::endl;
        std::cerr << "       " << argv[0] << " --help     Displays usage" << std::endl;
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
    std::vector<std::string> compute_host_names;
    unsigned long num_compute_hosts;

    try {
        // Read JSON input
        json_input = readJSONFromFile(argv[1]);
        // Override the workflow file spec if needed
        if (argc == 3) {
            json_input["workflow"].as_object()["file"] = std::string(argv[2]);
        }
        // Create the workflow for the WRENCH simulation
        workflow = create_workflow(json_input, &observed_real_makespan, &num_compute_hosts);

//        for (auto const &f : workflow->getFileMap()) {
//            std::cout << "---> " << f.first << " " << f.second->getSize()/(1024*1024*1024) << " IN GBYTES\n";
//        }

        if (num_compute_hosts <= 0) {
            throw std::invalid_argument("The Workflow JSON does not specify 'machines', and thus we can't determine "
                                        "the number of compute hosts used");
        }
        // Determine schemes in use
        determine_all_schemes(json_input, compute_service_scheme, storage_service_scheme, network_topology_scheme);
        // Create the platform
        PlatformCreator platform_creator(json_input, num_compute_hosts);
        simulation->instantiatePlatform(platform_creator);
        // Gather all relevant hostnames and perform sanity checks
        process_hostnames(submit_host_name, compute_host_names);

    } catch (std::invalid_argument &e) {
        std::cerr << "Error: " << e.what() << std::endl;
        exit(1);
    }

    // Create relevant storage services

    // There is always a storage service on the submit_node
    auto submit_node_storage_service =
            simulation->add(wrench::SimpleStorageService::createSimpleStorageService(
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
    submit_node_storage_service->setNetworkTimeoutValue(NETWORK_TIMEOUT);

    // Create relevant compute services
    std::set<std::shared_ptr<wrench::ComputeService>> compute_services;

    if (compute_service_scheme == "all_bare_metal") {

        std::string scratch_mount_point;
        if (storage_service_scheme == "submit_and_compute_hosts") {
            scratch_mount_point = "/scratch";
        } else {
            scratch_mount_point = "";
        }

        // Create one bare-metal service on all compute nodes
        for (auto const &host : compute_host_names) {
            auto cs = simulation->add(
                    new wrench::BareMetalComputeService(
                            host,
                            {host},
                            scratch_mount_point,
                            get_properties(json_input,
                                           "compute_service_scheme_parameters",
                                           compute_service_scheme,
                                           "properties"),
                            get_payloads(json_input,
                                         "compute_service_scheme_parameters",
                                         compute_service_scheme,
                                         "payloads")));
            cs->setNetworkTimeoutValue(NETWORK_TIMEOUT);
            if (not scratch_mount_point.empty()) {
                cs->getScratch()->setNetworkTimeoutValue(NETWORK_TIMEOUT);
            }
            compute_services.insert(cs);
        }

    } else if (compute_service_scheme == "htcondor_bare_metal") {
        // Create one bare-metal service on all compute nodes

        std::set<std::shared_ptr<wrench::ComputeService>> bare_metal_services;
        std::string scratch_mount_point;
        if (storage_service_scheme == "submit_and_compute_hosts") {
            scratch_mount_point = "/scratch";
        } else {
            scratch_mount_point = "";
        }
        for (auto const &host : compute_host_names) {
            auto cs = simulation->add(
                    new wrench::BareMetalComputeService(
                            host,
                            {host},
                            scratch_mount_point,
                            get_properties(json_input,
                                           "compute_service_scheme_parameters",
                                           compute_service_scheme,
                                           "bare_metal_properties"),
                            get_payloads(json_input,
                                         "compute_service_scheme_parameters",
                                         compute_service_scheme,
                                         "bare_metal_payloads")));
            cs->setNetworkTimeoutValue(NETWORK_TIMEOUT);
            bare_metal_services.insert(cs);
        }

        // Create a top-level HTCondor compute service
        auto htcondor_cs = simulation->add(
                new wrench::HTCondorComputeService(
                        submit_host_name,
                        bare_metal_services,
                        get_properties(json_input,
                                       "compute_service_scheme_parameters",
                                       compute_service_scheme,
                                       "htcondor_properties"),
                        get_payloads(json_input,
                                     "compute_service_scheme_parameters",
                                     compute_service_scheme,
                                     "htcondor_payloads")));
        htcondor_cs->setNetworkTimeoutValue(NETWORK_TIMEOUT);
        compute_services.insert(htcondor_cs);

    }

    // Instantiate a Controller on the submit_host
    double scheduling_overhead;
    try {
        scheduling_overhead = UnitParser::parse_time(boost::json::value_to<std::string>(json_input["scheduling_overhead"]));
    } catch (std::exception &e) {
        std::cerr << "Error: Invalid or missing scheduling_overhead specification in JSON input (" << e.what() <<  ")\n";
        exit(1);
    }

    auto wms = new wrench::Controller(workflow,
                                      compute_service_scheme,
                                      storage_service_scheme,
                                      compute_services,
                                      submit_node_storage_service,
                                      scheduling_overhead,
                                      submit_host_name);
    wms->setNetworkTimeoutValue(NETWORK_TIMEOUT);
    simulation->add(wms);

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

    double simulated_makespan = workflow->getCompletionDate();
    double err = std::fabs(observed_real_makespan - simulated_makespan) / observed_real_makespan;

    std::cout << simulated_makespan << ":" << observed_real_makespan << ":" << err << std::endl;

    return 0;
}
