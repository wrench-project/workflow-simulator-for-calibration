
/**
 * Copyright (c) 2017-2018. The WRENCH Team.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */


#ifndef CONTROLLER_H
#define CONTROLLER_H

#include <wrench-dev.h>

namespace wrench {

    /**
     *  @brief A Workflow Management System (WMS) implementation
     */
    class Controller : public ExecutionController {

    public:
        // Constructor
        Controller(
                std::shared_ptr<Workflow> workflow,
                std::string compute_service_scheme,
                std::string storage_service_scheme,
                std::set<std::shared_ptr<wrench::ComputeService>> compute_services,
                std::shared_ptr<wrench::StorageService> submit_node_storage_service,
                double scheduling_overhead,
                const std::string &hostname);

    protected:
        // Overridden method
        void processEventStandardJobCompletion(std::shared_ptr<StandardJobCompletedEvent>) override;
        void processEventStandardJobFailure(std::shared_ptr<StandardJobFailedEvent>) override;

    private:
        // main() method of the WMS
        int main() override;

        std::shared_ptr<Workflow> workflow;
        std::string compute_service_scheme;
        std::string storage_service_scheme;
        std::set<std::shared_ptr<wrench::ComputeService>> compute_services;
        std::shared_ptr<wrench::StorageService> submit_node_storage_service;
        double scheduling_overhead;

        std::map<std::shared_ptr<ComputeService>, unsigned long> core_availability;
    };
}// namespace wrench
#endif//CONTROLLER_H
