#include <string>

#include <wrench-dev.h>
#include <simgrid/s4u.hpp>

#include "UnitParser.h"
#include "PlatformCreator.h"

namespace sg4 = simgrid::s4u;

PlatformCreator::PlatformCreator(boost::json::object &json_spec) {
    this->json_spec = json_spec;
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

    // Getting host and disk specs
    boost::json::object host_specs;
    try {
        host_specs = this->json_spec["compute_service_scheme_parameters"].as_object()[
                this->json_spec["compute_service_scheme"].as_string()].as_object();
    } catch (std::exception &e)  {
        throw std::invalid_argument("Missing or invalid mapping between 'compute_service_scheme' and an entry in 'compute_service_scheme_parameters'");
    }
    boost::json::object disk_specs;
    try {
        disk_specs = this->json_spec["storage_service_scheme_parameters"].as_object()[
                this->json_spec["storage_service_scheme"].as_string()].as_object();
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

    // Create the slurm head host
    if (not host_specs.contains("slurm_head_host")) {
        throw std::invalid_argument("Missing or invalid value for 'slurm_head_host'");
    }
    auto slurm_head_spec = host_specs["slurm_head_host"].as_object();
    double slurm_head_speed;
    try {
        slurm_head_speed = UnitParser::parse_compute_speed(
                boost::json::value_to<std::string>(slurm_head_spec["speed"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for the slurm head host's 'speed'");
    }
    int slurm_head_num_cores;
    try {
        slurm_head_num_cores = std::stoi(boost::json::value_to<std::string>(slurm_head_spec["num_cores"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for the slurm head host's 'num_cores'");
    }

    auto slurm_head = zone->create_host("slurm_head", slurm_head_speed);
    slurm_head->set_core_count(slurm_head_num_cores);
    slurm_head->set_property("type", "slurm_head");

    // Create the disk on the slurm head host, if need be
    if (disk_specs.contains("slurm_head_disk_read") and disk_specs.contains("slurm_head_disk_write")) {
        try {
            UnitParser::parse_bandwidth(boost::json::value_to<std::string>(disk_specs["slurm_head_disk_read"]));
        } catch (std::exception &e) {
            throw std::invalid_argument("Missing or invalid 'slurm_head_disk_read' value");
        }
        try {
            UnitParser::parse_bandwidth(boost::json::value_to<std::string>(disk_specs["slurm_head_disk_write"]));
        } catch (std::exception &e) {
            throw std::invalid_argument("Missing or invalid 'slurm_head_disk_write' value");
        }

        auto slurm_head_disk = slurm_head->create_disk("slurm_head_hard_drive",
                                                       boost::json::value_to<std::string>(
                                                               disk_specs["slurm_head_disk_read"]),
                                                       boost::json::value_to<std::string>(
                                                               disk_specs["slurm_head_disk_write"]));
        slurm_head_disk->set_property("size", "5000GiB");
        slurm_head_disk->set_property("mount", "/");
    } else if (disk_specs.contains("slurm_head_disk_read") or disk_specs.contains("slurm_head_disk_write")) {
        throw std::invalid_argument("Both 'slurm_head_disk_read' and 'slurm_head_disk_write' must be specified");
    }

    // Create all compute hosts
    if (not host_specs.contains("compute_hosts")) {
        throw std::invalid_argument("Missing or invalid value for 'compute_hosts'");
    }
    auto compute_hosts_spec = host_specs["compute_hosts"].as_object();

    int num_compute_hosts;
    try {
        num_compute_hosts = std::stoi(boost::json::value_to<std::string>(compute_hosts_spec["num_hosts"]));
    } catch (std::exception  &e) {
        throw std::invalid_argument("Missing or invalid value for  compute_hosts's 'num_hosts'");
    }
    if (num_compute_hosts < 1) {
        throw std::invalid_argument("At least one compute host is needed");
    }
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
        compute_hosts.push_back(compute_host);
    }

    // Create links and routes
    boost::json::string topology_scheme;
    try {
        topology_scheme = this->json_spec["network_topology_scheme"].as_string();
    } catch (std::exception &e) {
        throw std::invalid_argument("Missing 'network_topology_scheme' entry");
    }
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
                boost::json::value_to<std::string>(link_specs["latency"]));

        // Create all routes
        {
            sg4::LinkInRoute network_link_in_route{network_link};
            zone->add_route(submit_host->get_netpoint(),
                            slurm_head->get_netpoint(),
                            nullptr,
                            nullptr,
                            {network_link_in_route});
            for (auto const &h : compute_hosts) {
                zone->add_route(submit_host->get_netpoint(),
                                h->get_netpoint(),
                                nullptr,
                                nullptr,
                                {network_link_in_route});
            }
        }

    } else if (topology_scheme == "two_links") {
        throw std::runtime_error("TWO_LINKS scheme not implemented yet");

    } else if (topology_scheme == "many_links") {
        throw std::runtime_error("MANU_LINKS scheme not implemented yet");

    } else {
        throw std::invalid_argument("Invalid 'network_topology_scheme' value");
    }


#if 0
    // Create a ComputeHost
    auto compute_host = zone->create_host("ComputeHost", "1Gf");
    compute_host->set_core_count(10);
    compute_host->set_property("ram", "16GB");

    // Create three network links
    auto network_link = zone->create_link("network_link", link_bw)->set_latency("20us");
    auto loopback_WMSHost = zone->create_link("loopback_WMSHost", "1000EBps")->set_latency("0us");
    auto loopback_ComputeHost = zone->create_link("loopback_ComputeHost", "1000EBps")->set_latency("0us");

    // Add routes
    {
        sg4::LinkInRoute network_link_in_route{network_link};
        zone->add_route(compute_host->get_netpoint(),
                        wms_host->get_netpoint(),
                        nullptr,
                        nullptr,
                        {network_link_in_route});
    }
    {
        sg4::LinkInRoute network_link_in_route{loopback_WMSHost};
        zone->add_route(wms_host->get_netpoint(),
                        wms_host->get_netpoint(),
                        nullptr,
                        nullptr,
                        {network_link_in_route});
    }
    {
        sg4::LinkInRoute network_link_in_route{loopback_ComputeHost};
        zone->add_route(compute_host->get_netpoint(),
                        compute_host->get_netpoint(),
                        nullptr,
                        nullptr,
                        {network_link_in_route});
    }

#endif

    zone->seal();
}