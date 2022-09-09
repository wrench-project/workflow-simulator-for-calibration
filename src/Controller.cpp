
/**
 * Copyright (c) 2017-2021. The WRENCH Team.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */

/**
 ** An execution controller to execute a workflow
 **/

#include <iostream>
#include <utility>

#include "Controller.h"

WRENCH_LOG_CATEGORY(controller, "Log category for Controller");

namespace wrench {

    /**
     * @brief Constructor
     *
     * @param workflow: the workflow to execute
     * @param bare_metal_compute_service: a set of compute services available to run tasks
     * @param storage_services: a set of storage services available to store files
     * @param hostname: the name of the host on which to start the WMS
     */
    Controller::Controller(std::shared_ptr<Workflow> workflow,
                           std::unordered_map<std::shared_ptr<wrench::ComputeService>,
                                   std::shared_ptr<wrench::StorageService>> compute_node_services,
                           std::shared_ptr<wrench::StorageService> submit_node_storage_service,
                           std::string data_scheme,
                           std::string compute_service_type,
                           double scheduling_overhead,
                           const std::string &hostname) : ExecutionController(hostname, "controller"),
                                                          workflow(std::move(workflow)),
                                                          compute_node_services(std::move(compute_node_services)),
                                                          submit_node_storage_service(std::move(submit_node_storage_service)),
                                                          data_scheme(std::move(data_scheme)),
                                                          compute_service_type(std::move(compute_service_type)),
                                                          scheduling_overhead(scheduling_overhead) {}

    /**
     * @brief main method of the Controller
     *
     * @return 0 on completion
     *
     * @throw std::runtime_error
     */
    int Controller::main() {


        /* Set the logging output to GREEN */
        TerminalOutput::setThisProcessLoggingColor(TerminalOutput::COLOR_GREEN);

        WRENCH_INFO("Controller starting");
        WRENCH_INFO("About to execute a workflow with %lu tasks", this->workflow->getNumberOfTasks());

        // Fill-in the potentially useful map of core availability (likely only useful for the bare_metal
        // compute service type)
        for (auto const &s : this->compute_node_services) {
            auto cs = s.first;
            unsigned long num_cores = 0;
            for (auto const &h :cs->getPerHostNumCores()) {
                num_cores += h.second;
            }
            this->core_availability[cs] = num_cores;
        }

        // Create a job manager so that we can create/submit jobs
        auto job_manager = this->createJobManager();

        // While the workflow isn't done, repeat the main loop
        while (not this->workflow->isDone()) {

            // Submit each ready task as a single job
            auto ready_tasks = this->workflow->getReadyTasks();

            for (auto const &ready_task: ready_tasks) {

                wrench::Simulation::sleep(this->scheduling_overhead);

                // Pick a target compute service (and service-specific arguments while we're at it)
                std::shared_ptr<ComputeService> target_cs = nullptr;
                std::map<std::string, std::string> service_specific_arguments;

                if (this->compute_service_type == "bare_metal") {
                    for (auto const &avail : this->core_availability) {
                        auto cs = avail.first;
                        auto count = avail.second;
                        if (count > 0) {
                            core_availability[cs] = count - 1;
                            target_cs = cs;
                            break;
                        }
                    }
                } else {
                    throw std::runtime_error("Unimplemented compute_service_type in the Controller: " + compute_service_type);
                }

                if (!target_cs) {
                    break; // couldn't schedule the task, for whatever reason
                }

                // Create a standard job for the task
                WRENCH_INFO("Creating a job for task %s", ready_task->getID().c_str());

                // Create the job info
                std::vector<std::shared_ptr<WorkflowTask>> tasks = {ready_task};
                std::map<std::shared_ptr<DataFile>, std::shared_ptr<FileLocation>> file_locations;
                std::vector<std::tuple<std::shared_ptr<DataFile>, std::shared_ptr<FileLocation>, std::shared_ptr<FileLocation>>> pre_file_copies;
                std::vector<std::tuple<std::shared_ptr<DataFile>, std::shared_ptr<FileLocation>, std::shared_ptr<FileLocation>>> post_file_copies;
                std::vector<std::tuple<std::shared_ptr<DataFile>, std::shared_ptr<FileLocation>>> cleanup_file_deletions;

                // Data scheme
                if (data_scheme == "all_remote_streaming") {
                    for (auto const &f: ready_task->getInputFiles()) {
                        file_locations[f] = FileLocation::LOCATION(this->compute_node_services[target_cs]);
                        pre_file_copies.emplace_back(f,
                                                     FileLocation::LOCATION(this->submit_node_storage_service),
                                                     FileLocation::LOCATION(this->compute_node_services[target_cs]));
                    }
                    for (auto const &f: ready_task->getOutputFiles()) {
                        file_locations[f] = FileLocation::LOCATION(this->compute_node_services[target_cs]);
                        post_file_copies.emplace_back(f,
                                                      FileLocation::LOCATION(this->compute_node_services[target_cs]),
                                                      FileLocation::LOCATION(this->submit_node_storage_service));
                    }

                } else if (data_scheme == "copy_to_local_and_back_to_remote") {
                    for (auto const &f: ready_task->getInputFiles()) {
                        file_locations[f] = FileLocation::LOCATION(submit_node_storage_service);
                    }
                    for (auto const &f: ready_task->getOutputFiles()) {
                        file_locations[f] = FileLocation::LOCATION(submit_node_storage_service);
                    }
                } else {
                    throw std::runtime_error("Unimplemented data_scheme in the Controller: " + data_scheme);
                }


                // Create the job
                auto standard_job = job_manager->createStandardJob(tasks,
                                                                   file_locations,
                                                                   pre_file_copies,
                                                                   post_file_copies,
                                                                   cleanup_file_deletions
                );

                // Submit the job to the compute service
                WRENCH_INFO("Submitting the job to the compute service");
                job_manager->submitJob(standard_job, target_cs, service_specific_arguments);
            }

            // Wait for a workflow execution event and process it
            this->waitForAndProcessNextEvent();
        }

        WRENCH_INFO("Workflow execution complete!");
        return 0;
    }

    /**
     * @brief Process a standard job completion event
     *
     * @param event: the event
     */
    void Controller::processEventStandardJobCompletion(std::shared_ptr<StandardJobCompletedEvent> event) {
        auto job = event->standard_job;
        auto task = job->getTasks().at(0);
        WRENCH_INFO("Notified that a standard job has completed task %s", task->getID().c_str());
    }

    /**
     * @brief Process a standard job failure event
     *
     * @param event: the event
     */
    void Controller::processEventStandardJobFailure(std::shared_ptr<StandardJobFailedEvent> event) {
        auto job = event->standard_job;
        auto task = job->getTasks().at(0);
        WRENCH_INFO("Notified that a standard job has failed for task %s (%s)",
                    task->getID().c_str(),
                    event->failure_cause->toString().c_str());
    }

}// namespace wrench
