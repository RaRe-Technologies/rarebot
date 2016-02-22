#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 RaRe Technologies s.r.o.
# Author: Jan Rygl <jimmy@rare-technologies.com>
# All Rights Reserved

"""USAGE: %(program)s -h

Examples:
    # See all parameters:
    ./example.py -h

    # Simulate standard program run:
    ./example.py

    # Simulate all errors:
    ./example.py -l -f -u -r
"""
import os
import sys
import json
import argparse
import datetime
import time


date_format = "%Y-%m-%d %H:%M:%S"


def main(
        simulate_late_report=True, simulate_format_error=True, simulate_unseen_error=True,
        simulate_repeted_error=True, simulate_timeout_error=True):
    """
    Read from stdin and write to stdout.

    Args:
        simulate_late_report (bool): turn on/off
        simulate_format_error (bool): turn on/off
        simulate_unseen_error (bool): turn on/off
        simulate_repeted_error (bool): turn on/off
        simulate_timeout_error (bool): turn on/off

    """
    line_counter = -1
    while True:  # repeat until empty line
        line_counter += 1
        line = sys.stdin.readline()  # read line from stdin (including \n character)
        # count your time
        loop_start_time = time.time()

        if not line or line.strip() == 'exit':  # if line is empty or exit string, break loop
            # +----------------------------------------------------+
            # | before the end of script, you can report anomalies |
            # +----------------------------------------------------+
            if line_counter > 1:
                # report last line as anomaly to demonstrate functionality
                sys.stdout.write('%i\n' % (line_counter - 1))
                sys.stdout.flush()
            # write `ok\n` for system not to wait for another output
            sys.stdout.write('ok\n')
            sys.stdout.flush()
            # +----------------------------------------------------+
            # break to end infinite loop
            break

        # convert JSON serialized string to object (Python dict)
        activity_log = json.loads(line)

        # timestamp of event
        timestamp = datetime.datetime.fromtimestamp(int(activity_log["unix_timestamp"]))

        # +----------------------------------------------------+
        # | report this or older events before writing `ok\n`  |
        # +----------------------------------------------------+
        is_alarm = False
        if timestamp.isoweekday() > 4:
            # alarm for all events on Fri, Sat and Sun
            is_alarm = True
        if timestamp.second == 0:
            # alarm for all events occurring with 0 seconds timestamps
            is_alarm = True
        if is_alarm:
            sys.stdout.write(str(activity_log['id']) + '\n')
            sys.stdout.flush()

        # +----------------------------------------------------+
        # | examples of bad code                               |
        # +----------------------------------------------------+
        # late reporting (you must report anomaly for event E1
        # after acceptance of the first event E2 older than
        # E1 by at least 1 hour (time(E2) > time(E1) + 1 hour
        if simulate_late_report and line_counter == 13:
            sys.stdout.write('4\n')
            sys.stdout.flush()

        # to report the event, output its id (int) and newline
        if simulate_format_error and line_counter == 7:
            sys.stdout.write('EVENT 0\n')
            sys.stdout.flush()

        # don't report ids which weren't sent to you yet
        if simulate_unseen_error and line_counter == 15:
            sys.stdout.write('17\n')
            sys.stdout.flush()

        # reporting one event several times won't break
        # anything, but it will spam logs
        if simulate_repeted_error and line_counter == 3:
            sys.stdout.write('3\n')
            sys.stdout.flush()
            sys.stdout.write('3\n')
            sys.stdout.flush()
        if simulate_timeout_error and line_counter == 10:
            time.sleep(3)
        # +----------------------------------------------------+
        # write `ok\n` to continue loop (only if we didn't exceed time limit)
        if time.time() - loop_start_time < 2:
            sys.stdout.write('ok\n')
            # don't forget to flush stdout
            sys.stdout.flush()


if __name__ == '__main__':
    # check and process cmdline input
    program = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
        prog=program,
        formatter_class=argparse.RawTextHelpFormatter,
        description=globals()['__doc__'])

    parser.add_argument('-l', '--late-report', action='store_true', help="simulate late reporting error")
    parser.add_argument('-f', '--format-error', action='store_true', help="simulate invalid format error")
    parser.add_argument('-u', '--unseen-error', action='store_true', help="simulate reporting unseen event error")
    parser.add_argument('-r', '--repeated-report', action='store_true', help="simulate reporting one event twice")
    parser.add_argument('-t', '--timeout-error', action='store_true', help="simulate no answer for 2s")

    args = parser.parse_args()
    main(
        simulate_late_report=args.late_report,
        simulate_format_error=args.format_error,
        simulate_unseen_error=args.unseen_error,
        simulate_repeted_error=args.repeated_report,
        simulate_timeout_error=args.timeout_error
        )
