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

    // Get hosts and disk specs
    auto host_specs = this->json_spec["compute_service_scheme_parameters"].as_object()[
            this->json_spec["compute_service_scheme"].as_string()].as_object();
    auto disk_specs = this->json_spec["storage_service_scheme_parameters"].as_object()[
            this->json_spec["storage_service_scheme"].as_string()].as_object();

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
    slurm_head->set_property("type", "submit");

    // Create the disk on the submit host, if need be
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

    // Create all compute nodes

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