#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 RaRe Technologies s.r.o.
# Author: Jan Rygl <jimmy@rare-technologies.com>
# All Rights Reserved

"""USAGE:

Run example script:
    ./evaluator.py --log example.log --script ./example.py

Run example script with parameters:
    ./evaluator.py --logs example.log --script "./example.py -l -f -u -r "

Run your script without parameters:
    ./evaluator.py --logs competition.log --script ./your_script.extension

Run your script with parameters:
    ./evaluator.py --logs competition.log --script "./your_script.extension --par1 val1 --par2 val2"
"""

from __future__ import print_function

import sys
import os
import argparse
import logging
from subprocess import PIPE, Popen
from threading import Thread
from Queue import Queue, Empty
import time
import json
import datetime


TIME_LIMIT = 2
PROGRAM_TIME_LIMIT = 600


class Evaluator(object):

    def __init__(self, activity_access_log_path):
        """
        Args:
            activity_access_log_path: path to logs for testing
        """
        self.file_handler = open(activity_access_log_path)
        self.anomalies = []
        self.users = []
        self.alarms = []
        self.date_format = "%Y-%m-%d %H:%M:%S"
        self.last_two_timestamps = [None, None]  # remember last two timestamps
        self.event_timestamps = {}  # dict event_id=>timestamp

    def _get_inner_time(self):
        """
        Inner time is the timestamp of the penultimate event sent to contestants.

        Returns:
            timestamp string (zero time if 0 or 1 event was sent to contestants)
        """
        timestamp = self.last_two_timestamps[0]
        if not timestamp:
            return '0000-00-00 00:00:00'
        return str(timestamp)

    def events(self):
        """
        Generator of event activity logs as JSON serialized strings per line.

        Returns: (event_id, event_JSON_serialized_as_string)

        """
        for line_num, line in enumerate(self.file_handler):
            if not line:
                break
            # process line input to dictionary
            data = json.loads(line)
            # add id information
            data['id'] = line_num
            # update timestamp history
            timestamp = self._get_timestamp(data)
            self.last_two_timestamps = [self.last_two_timestamps[-1], timestamp]
            self.event_timestamps[line_num] = timestamp

            self.alarms.append(0)  # add field for alarms
            self.users.append(data['employee'])  # add field for employee
            self.anomalies.append(data.get('is_anomaly', 0))  # add field for anomalies
            if 'is_anomaly' in data:
                del data['is_anomaly']  # remove anomaly information from data for contestants

            # return line id and serialized JSON as string representing one event
            str_dump = json.dumps(data)
            logger.info(self._get_inner_time() + ' > ' + str_dump)
            yield line_num, str_dump

    def _get_timestamp(self, event_dict):
        """
        Args:
            event_dict: dict containing field `event_dict`

        Returns:
            datetime extracted from dict field `unix_timestamp`

        """
        return datetime.datetime.fromtimestamp(int(event_dict["unix_timestamp"]))  # timestamp of event

    def _anomaly_check(self, line):
        """
        Check if anomaly is reported in time, it is readable, not repeated and legal (event_id exists).
        Store information about reported anomaly.

        Args:
            line (str): activity log as serialized JSON as string

        """
        logger.info(self._get_inner_time() + ' < %s', line.strip())
        if not line or not line.strip().isdigit():
            # format error
            logger.error(self._get_inner_time() + ' ! `%s` can\'t be parsed, int is required', line)
            return

        num = int(line.strip())
        if num in self.event_timestamps:
            # check if not already reported
            if self.alarms[num]:
                logger.error(self._get_inner_time() + ' ! you have already reported event n. %i', num)
            else:
                # check age of event
                last_allowed_timestamp = self.event_timestamps[num] + datetime.timedelta(hours=1)
                if self.last_two_timestamps[0] is None or self.last_two_timestamps[0] <= last_allowed_timestamp:
                    self.alarms[num] = 1
                else:
                    logger.error(
                        self._get_inner_time() +
                        ' ! late event %i reporting (event: %s, you already read events: %s and %s)',
                        num, self.event_timestamps[num], self.last_two_timestamps[0], self.last_two_timestamps[1])
        else:
            logger.error(
                self._get_inner_time() + ' ! you are forbidden to predict event %i that you haven\'t seen yet', num)

    def process_msg(self, msg, event_string, line_id):
        """
        Process output of contestants' script and inform about result to log output.
        Two allowed inputs:
            `ok\n`: contestants' script is ready for next event log
            `[0-9]+\n`: contestants' script reports anomaly for event id [0-9]+

        Args:
            msg (str): message from the stdout of the contestants' script (or None for no answer)
            event_string (str): activity log sent to the contestants' script
            line_id (int): id of activity log stored in `event_string`

        Returns:
            True to stop asking (ok was returned), otherwise False

        """
        if msg is None:
            if line_id == -1:
                # all events are known and we don't want to report anything else
                logger.info(self._get_inner_time() + ' end of simulation')
            else:
                # failed to answer in time limit
                logger.error(self._get_inner_time() + ' ! %i: no answer', line_id)
            return True
        if msg.strip().lower() == 'ok':
            if line_id == -1:
                # all events are known and we don't want to report anything else
                logger.info(self._get_inner_time() + ' end of simulation')
                return True
            else:
                logger.info(self._get_inner_time() + ' < ok')
                return True
        else:
            self._anomaly_check(msg)
            return False

    def finish(self):
        """Count F-measure and output script evaluation to stdout.
        """
        distinct_users = set(self.users)

        output = []
        f_measures = []
        for user in distinct_users:
            output.append(user)
            tp, tn, fp, fn = 0.0, 0.0, 0.0, 0.0
            for reported, present, event_user in zip(self.alarms, self.anomalies, self.users):
                if event_user != user:
                    continue
                if present and reported:
                    tp += 1
                elif not present and not reported:
                    tn += 1
                elif not present and reported:
                    fp += 1
                elif present and not reported:
                    fn += 1
            output.append('True positive:  %i' % tp)
            output.append('True negative:  %i' % tn)
            output.append('False positive: %i' % fp)
            output.append('False negative: %i' % fn)
            if tp == 0:
                f_measure = 0
            else:
                f_measure = 2.0 * tp / (2 * tp + fn + fp)
            f_measures.append(f_measure)
            output.append('F-measure:      %0.4f' % f_measure)
            output.append('-------------------------------------')
        avg_f_measure = 1.0 * sum(f_measures) / len(f_measures)
        output.append('Score (avg. user F-measure): %0.6f' % avg_f_measure)
        str_output = '\n'.join(output)
        print(str_output)
        logger.debug(str_output)


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def main(command, log_path):
    """

    Args:
        command:
        log_path:

    Returns:

    """
    logger.debug('PREPARING: %s', datetime.datetime.today())
    logger.info('preparing simulation')
    program_timer = time.time()
    ON_POSIX = 'posix' in sys.builtin_module_names
    competition_process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=1, close_fds=ON_POSIX)
    queue = Queue()
    thread = Thread(target=enqueue_output, args=(competition_process.stdout, queue))
    thread.daemon = True # thread dies with the program
    thread.start()

    ev = Evaluator(log_path)
    logger.debug('REAL START: %s', datetime.datetime.today())
    logger.info(ev._get_inner_time() + ' start of simulation')
    for line_id, event_string in ev.events():
        if not event_string:
            break
        competition_process.stdin.write(event_string + '\n')
        competition_process.stdin.flush()
        start = time.time()
        while True:
            msg = None
            while time.time() - start <= TIME_LIMIT:
                try:
                    msg = queue.get(timeout=0.2).strip()
                    break
                except Empty:
                    pass
            if ev.process_msg(msg, event_string, line_id):
                break

    logger.info(ev._get_inner_time() + ' last opportunity to report anomalies')
    competition_process.stdin.write('exit\n')
    competition_process.stdin.flush()
    start = time.time()
    while True:
        msg = None
        while time.time() - start <= TIME_LIMIT * 2:
            try:
                msg = queue.get(timeout=0.2)
                break
            except Empty:
                pass
        if ev.process_msg(msg, '', -1):
            break

    logger.debug('REAL END: %s', datetime.datetime.today())
    assert program_timer - time.time() <= PROGRAM_TIME_LIMIT
    ev.finish()


if __name__ == '__main__':
    # logging
    logger = logging.getLogger(__name__)
    file_log = logging.FileHandler('evaluator.log')  # create file handler
    file_log.setLevel(logging.DEBUG)
    stderr_log = logging.StreamHandler()  # create console handler with a higher log level
    stderr_log.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    stderr_log.setFormatter(formatter)
    file_log.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(stderr_log)
    logger.addHandler(file_log)
    logger.setLevel(logging.DEBUG)
    logger.info("running %s", " ".join(sys.argv))

    # check and process cmdline input
    program = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
        prog=program,
        formatter_class=argparse.RawTextHelpFormatter,
        description=globals()['__doc__'])
    parser.add_argument(
        '-l', '--logs', required=True,
        help="path to a file with activity logs for testing")
    parser.add_argument(
        '-s', '--script', required=True,
        help="path to a script to evaluate logs, to include parameters, wrap parameters into quotes")

    args = parser.parse_args()
    main(args.script.split(), args.logs)
    logger.info("finished running %s", program)
