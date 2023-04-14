#include <string>

#include <wrench-dev.h>
#include <simgrid/s4u.hpp>

#include "UnitParser.h"
#include "PlatformCreator.h"

namespace sg4 = simgrid::s4u;

PlatformCreator::PlatformCreator(boost::json::object &json_spec, unsigned long num_compute_hosts) {
    this->json_spec = json_spec;
    this->num_compute_hosts = num_compute_hosts;
}

void PlatformCreator::create_platform() {

    // Create the top-level zone
    auto zone = sg4::create_full_zone("AS0");

    // Get compute, storage, and topology schemes
    boost::json::string compute_service_scheme;
    try {
        compute_service_scheme = this->json_spec["compute_service_scheme"].as_string();
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing 'compute_service_scheme' entry");
    }
    boost::json::string storage_service_scheme;
    try {
        storage_service_scheme = this->json_spec["storage_service_scheme"].as_string();
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing 'storage_service_scheme' entry");
    }
    boost::json::string topology_scheme;
    try {
        topology_scheme = this->json_spec["network_topology_scheme"].as_string();
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing 'network_topology_scheme' entry");
    }

    // Getting host and disk specs
    boost::json::object host_specs;
    try {
        host_specs = this->json_spec["compute_service_scheme_parameters"].as_object()[
                compute_service_scheme].as_object();
    } catch (std::exception &e)  {
        throw std::invalid_argument("Missing or invalid mapping between 'compute_service_scheme' and an entry in 'compute_service_scheme_parameters'");
    }
    boost::json::object disk_specs;
    try {
        disk_specs = this->json_spec["storage_service_scheme_parameters"].as_object()[
                storage_service_scheme].as_object();
    } catch (std::exception &e)  {
        throw std::invalid_argument("Missing or invalid mapping between 'storage_service_scheme' and an entry in 'storage_service_scheme_parameters'");
    }

    // Create the submit host
    if (not host_specs.contains("submit_host")) {
        throw std::invalid_argument("Missing or invalid value for 'submit_host'");
    }
    auto submit_host_spec = host_specs["submit_host"].as_object();
    double submit_host_speed;
    try {
        submit_host_speed = UnitParser::parse_compute_speed(
                boost::json::value_to<std::string>(submit_host_spec["speed"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for the submit host's 'speed'");
    }
    int submit_host_num_cores;
    try {
        submit_host_num_cores = std::stoi(boost::json::value_to<std::string>(submit_host_spec["num_cores"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for the submit host's 'num_cores'");
    }

    auto submit_host = zone->create_host("submit_host", submit_host_speed);
    submit_host->set_core_count(submit_host_num_cores);
    submit_host->set_property("type", "submit");

    // Create the disk on the submit host
    try {
        UnitParser::parse_bandwidth(boost::json::value_to<std::string>(disk_specs["bandwidth_submit_disk_read"]));
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing or invalid 'bandwidth_submit_disk_read' value");
    }
    try {
        UnitParser::parse_bandwidth(boost::json::value_to<std::string>(disk_specs["bandwidth_submit_disk_write"]));
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing or invalid 'bandwidth_submit_disk_write' value");
    }

    auto submit_host_disk = submit_host->create_disk("submit_host_hard_drive",
                                                     boost::json::value_to<std::string>(disk_specs["bandwidth_submit_disk_read"]),
                                                     boost::json::value_to<std::string>(disk_specs["bandwidth_submit_disk_write"]));
    submit_host_disk->set_property("size", "5000GiB");
    submit_host_disk->set_property("mount", "/");

    // Create all compute hosts
    if (not host_specs.contains("compute_hosts")) {
        throw std::invalid_argument("Missing or invalid value for 'compute_hosts'");
    }
    auto compute_hosts_spec = host_specs["compute_hosts"].as_object();

    double compute_host_speed;
    try {
        compute_host_speed = UnitParser::parse_compute_speed(
                boost::json::value_to<std::string>(compute_hosts_spec["speed"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for compute_hosts's 'speed'");
    }
    int compute_host_num_cores;
    try {
        compute_host_num_cores = std::stoi(boost::json::value_to<std::string>(compute_hosts_spec["num_cores"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for compute_hosts's 'num_cores'");
    }

    std::vector<sg4::Host*> compute_hosts;
    for (int i=0; i < num_compute_hosts; i++) {
        auto compute_host = zone->create_host("compute_host_" + std::to_string(i), compute_host_speed);
        compute_host->set_core_count(compute_host_num_cores);
        compute_host->set_property("type", "compute");

        if (storage_service_scheme == "submit_and_compute_hosts") {
            // Create the scratch disk on the compute host
            try {
                UnitParser::parse_bandwidth(
                        boost::json::value_to<std::string>(disk_specs["bandwidth_compute_host_disk_read"]));
            } catch (std::exception &e) {
                throw std::invalid_argument("Missing or invalid 'bandwidth_compute_host_disk_read' value");
            }
            try {
                UnitParser::parse_bandwidth(
                        boost::json::value_to<std::string>(disk_specs["bandwidth_compute_host_write"]));
            } catch (std::exception &e) {
                throw std::invalid_argument("Missing or invalid 'bandwidth_compute_host_write' value");
            }

            auto scratch_disk = compute_host->create_disk("scratch_" + std::to_string(i),
                                                         boost::json::value_to<std::string>(
                                                                 disk_specs["bandwidth_compute_host_disk_read"]),
                                                         boost::json::value_to<std::string>(
                                                                 disk_specs["bandwidth_compute_host_write"]));
            scratch_disk->set_property("size", "500000EiB");
            scratch_disk->set_property("mount", "/scratch");
        }

        compute_hosts.push_back(compute_host);
    }

    // Create links and routes
    auto link_specs = this->json_spec["network_topology_scheme_parameters"].as_object()[topology_scheme].as_object();

    if (topology_scheme == "one_link") {

        // Create network link
        double bandwidth;
        try {
            bandwidth = UnitParser::parse_bandwidth(
                    boost::json::value_to<std::string>(link_specs["bandwidth"]));
        } catch (std::exception  &e) {
            throw std::invalid_argument("Missing or invalid 'bandwidth' value for 'one_link' scheme");
        }
        try {
            UnitParser::parse_time(
                    boost::json::value_to<std::string>(link_specs["latency"]));
        } catch (std::exception  &e) {
            throw std::invalid_argument("Missing or invalid 'latency' value for 'one_link' scheme");
        }

        auto network_link = zone->create_link("network_link", bandwidth)->set_latency(
                boost::json::value_to<std::string>(link_specs["latency"]))->seal();

        sg4::LinkInRoute network_link_in_route{network_link};

        for (auto const &h : compute_hosts) {
            zone->add_route(submit_host->get_netpoint(),
                            h->get_netpoint(),
                            nullptr,
                            nullptr,
                            {network_link_in_route}, true);
        }

    } else if (topology_scheme == "one_and_then_many_links") {

        // Create out_of_submit network link
        double bandwidth_out_of_submit;
        try {
            bandwidth_out_of_submit = UnitParser::parse_bandwidth(
                    boost::json::value_to<std::string>(link_specs["bandwidth_out_of_submit"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'bandwidth_out_of_submit' value for 'one_and_then_many_links' scheme");
        }
        try {
            UnitParser::parse_time(
                    boost::json::value_to<std::string>(link_specs["latency_out_of_submit"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'latency_out_of_submit' value for 'one_and_then_many_links' scheme");
        }
        auto network_link_out_of_submit = zone->create_link("network_link_out_of_submit",
                                                            bandwidth_out_of_submit)->set_latency(
                boost::json::value_to<std::string>(link_specs["latency_out_of_submit"]))->seal();

        // Create all to_compute_host network links
        double bandwidth_to_compute_hosts;
        try {
            bandwidth_to_compute_hosts = UnitParser::parse_bandwidth(
                    boost::json::value_to<std::string>(link_specs["bandwidth_to_compute_hosts"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'bandwidth_to_compute_hosts' value for 'one_and_then_many_links' scheme");
        }
        try {
            UnitParser::parse_time(
                    boost::json::value_to<std::string>(link_specs["latency_to_compute_hosts"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'latency_to_compute_hosts' value for 'one_and_then_many_links' scheme");
        }
        std::vector<sg4::Link *> network_links_to_compute_hosts;
        for (int i = 0; i < num_compute_hosts; i++) {
            auto link = zone->create_link("network_link_compute_host_" + std::to_string(i),
                                          bandwidth_to_compute_hosts)->set_latency(
                    boost::json::value_to<std::string>(link_specs["latency_to_compute_hosts"]))->seal();
            network_links_to_compute_hosts.emplace_back(link);
        }

        // Create all routes
        sg4::LinkInRoute network_link_in_route_1{network_link_out_of_submit};

        for (int i=0; i < compute_hosts.size(); i++) {
            sg4::LinkInRoute network_link_in_route_2{network_links_to_compute_hosts.at(i)};
            zone->add_route(submit_host->get_netpoint(),
                            compute_hosts.at(i)->get_netpoint(),
                            nullptr,
                            nullptr,
                            {network_link_in_route_1, network_link_in_route_2});
        }

    } else if (topology_scheme == "many_links") {

        // Create out_of_submit network link
        double bandwidth;
        try {
            bandwidth = UnitParser::parse_bandwidth(
                    boost::json::value_to<std::string>(link_specs["bandwidth_submit_to_compute_host"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'bandwidth_submit_to_compute_host' value for 'many_links' scheme");
        }
        try {
            UnitParser::parse_time(
                    boost::json::value_to<std::string>(link_specs["latency_submit_to_compute_host"]));
        } catch (std::exception &e) {
            throw std::invalid_argument(
                    "Missing or invalid 'latency_submit_to_compute_host' value for 'many_links' scheme");
        }

        // Create all to_compute_host network links
        std::vector<sg4::Link *> network_links_to_compute_hosts;
        for (int i = 0; i < num_compute_hosts; i++) {
            auto link = zone->create_link("network_link_compute_host_" + std::to_string(i),
                                          bandwidth)->set_latency(
                    boost::json::value_to<std::string>(link_specs["latency_submit_to_compute_host"]))->seal();
            network_links_to_compute_hosts.emplace_back(link);
        }

        // Create all routes
        for (int i=0; i < compute_hosts.size(); i++) {
            sg4::LinkInRoute network_link_in_route_1{network_links_to_compute_hosts.at(i)};
            zone->add_route(submit_host->get_netpoint(),
                            compute_hosts.at(i)->get_netpoint(),
                            nullptr,
                            nullptr,
                            {network_link_in_route_1});
        }

    } else {
        throw std::invalid_argument("Invalid 'network_topology_scheme' value");
    }

    zone->seal();
}