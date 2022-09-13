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

    // Create the submit host
    auto submit_host_spec = this->json_spec["compute_service_scheme_parameters"].as_object()[
            this->json_spec["compute_service_scheme"].as_string()].as_object()["submit_host"].as_object();
    double submit_host_speed = UnitParser::parse_compute_speed(boost::json::value_to<std::string>(submit_host_spec["speed"]));
    int submit_host_num_cores = (int) submit_host_spec["cores"].as_uint64();

    auto wms_host = zone->create_host("submit_host", submit_host_speed);
    wms_host->set_core_count(submit_host_num_cores);
    wms_host->set_property("type", "submit");

    // Create the disk on the submit host
    auto submit_disk_spec = this->json_spec["storage_service_scheme_parameters"].as_object()[
            this->json_spec["storage_service_scheme"].as_string()].as_object();




    auto wms_host_disk = wms_host->create_disk("hard_drive",
                                               "100MBps",
                                               "100MBps");
    wms_host_disk->set_property("size", "5000GiB");
    wms_host_disk->set_property("mount", "/");

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

    zone->seal();
}