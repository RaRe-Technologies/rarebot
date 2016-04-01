#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
# Author: Josef Samanek, 139911

import os
import sys
import json
import argparse
import datetime
import time

import pickle

date_format = "%Y-%m-%d %H:%M:%S"

# map activity_log values onto the same numbers as in training, split time, etc.
def prepLine(lineDict, mappings):
    result = []
    if lineDict['category'] in mappings['category']:
        result.append(mappings['category'].index(lineDict['category']))
    else:
        result.append(-1)
        
    if lineDict['behaviour'] in mappings['behaviour']:
        result.append(mappings['behaviour'].index(lineDict['behaviour']))
    else:
        result.append(-1)
        
    if lineDict['connection'] in mappings['connection']:
        result.append(mappings['connection'].index(lineDict['connection']))
    else:
        result.append(-1)
        
    day = datetime.datetime.fromtimestamp(lineDict['unix_timestamp']).weekday()
    time = datetime.datetime.fromtimestamp(lineDict['unix_timestamp']).time()
    seconds = time.hour*3600 + time.minute*60 + time.second
    result.append(day)
    result.append(seconds)
    #result.append(time.hour)
    
    if lineDict['safe_connection'] in mappings['safe_connection']:
        result.append(mappings['safe_connection'].index(lineDict['safe_connection']))
    else:
        result.append(-1)
    return [result] # wrap result in a list to be directly usable in model.predict (todo: test if it is necessary)


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

    # get script directory
    #dirName = os.path.dirname(os.path.realpath(__file__))

    # load users
    #filename = dirName + '/users.pkl'
    filename = './users.pkl'
    users = []
    with open(filename, 'rb') as usersFile:
        users = pickle.load(usersFile)

    # load value mappings
    #filename = dirName + '/mappings.pkl'
    filename = './mappings.pkl'
    mappings = {}
    with open(filename, 'rb') as mappingsFile:
        mappings = pickle.load(mappingsFile)


    # load models and scalers (for each user)
    models = {}
    scalers = {}
    for user in users:
        #filename = dirName + '/' + user +  '.pkl'
        filename = './' + user +  '.pkl'
        with open(filename, 'rb') as modelFile:
            models[user] = pickle.load(modelFile)

        #filename = dirName + '/' + user +  '_scaler.pkl'
        filename = './' + user +  '_scaler.pkl'
        with open(filename, 'rb') as scalerFile:
            scalers[user] = pickle.load(scalerFile)
    
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
            #if line_counter > 1:
                # report last line as anomaly to demonstrate functionality
                #sys.stdout.write('%i\n' % (line_counter - 1))
                #sys.stdout.flush()
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


        user = activity_log['user']
	# get day and time and map values to numbers according to learned mappings
        mappedLog = prepLine(activity_log, mappings)
	# scale (subtract mean and divide by variance or sthg like that)
        mappedLogNorm = scalers[user].transform(mappedLog)
	# predict if normal or anomaly
        prediction = models[user].predict(mappedLogNorm)
	# if anomaly, print it's id
        if prediction == -1:
            sys.stdout.write(str(activity_log['id']) + '\n')
            sys.stdout.flush()
     

        # +----------------------------------------------------+
        # write `ok\n` to continue loop (only if we didn't exceed time limit)
        if time.time() - loop_start_time < 2:
            sys.stdout.write('ok\n')
            # don't forget to flush stdout
            sys.stdout.flush()


if __name__ == '__main__':
    main()
    # check and process cmdline input    
    '''
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
    '''
