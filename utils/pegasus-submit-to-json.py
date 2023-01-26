#!/usr/bin/env python3
#
# Copyright (c) 2022. Loïc Pottier <pottier1@llnl.gov>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import pathlib
import argparse
from wfcommons.wfinstances import PegasusLogsParser

def convert(target_dir: str,
            workflow_name: str,
            output: str,
            ignore_auxiliary: bool,
            recursive: bool
            ):
    # creating the parser for the Pegasus workflow
    submit_dir = pathlib.Path(target_dir)
    if recursive:
        from wfcommons.wfinstances import HierarchicalPegasusLogsParser
        parser = HierarchicalPegasusLogsParser(
            submit_dir=submit_dir, ignore_auxiliary=ignore_auxiliary)
        workflow = parser.workflow
    else:
        parser = PegasusLogsParser(
            submit_dir=submit_dir, ignore_auxiliary=ignore_auxiliary)
        # generating the workflow instance object
        workflow = parser.build_workflow(workflow_name)

    # writing the workflow instance to a JSON file
    workflow_path = pathlib.Path(output)
    workflow.write_json(workflow_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert a Pegasus submit \
        directory to a JSON workflow compatible with WRENCH-based simulators.')

    parser.add_argument('--input-dir', '-i', dest='dir', action='store',
                        type=str, required=True,
                        help='Path of the Pegasus submit directory.')
    parser.add_argument('--output', '-o', action='store', type=str,
                        required=True, default="workflow.json",
                        help='Name of the JSON file produced')
    parser.add_argument('--name', '-w', action='store', type=str,
                        required=False, default="pegasus-workflow",
                        help='Name of the workflow in the JSON data')
    parser.add_argument('--recursive', '-r', action='store_true',
                        help='Must be set if the submit directory is a hierarchical workflow.')
    parser.add_argument('--ignore-aux', '-a', action='store_true',
                        help='If set, the parser will ignore auxiliary jobs used internally by Pegasus.')

    args = parser.parse_args()

    wfname = pathlib.Path(args.output).with_suffix('')
    # Safety check to make sure it has JSON extension
    output = wfname.with_suffix('.json')

    convert(
        target_dir=args.dir,
        workflow_name=str(wfname),
        output=str(output),
        ignore_auxiliary=args.ignore_aux,
        recursive=args.recursive
    )
