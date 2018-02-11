#!/usr/bin/env python

try:
    import re
    import sys
    import signal
    import argparse
    from time import sleep,time
    from datetime import datetime
    from pytz import timezone
    from elasticsearch import Elasticsearch
except Exception, e:
    print('ERROR: import modules failed')
    print('Exception %s' % e)
    exit(1)

try:
    #Argument Parsing
    parser = argparse.ArgumentParser(description='Command line tool for tailing logs from elasticsearch',formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-I', '-index', help='Index to query, defaults to _all', default='_all', dest='index', metavar='')
    parser.add_argument('-S', '--size', help='Number of results to show, defaults to 1000', default=1000, dest='size', metavar='')
    parser.add_argument('-H','--hostname', nargs='*', help='Hostname list', dest='hostname', metavar='HOST')
    parser.add_argument('-T', '--type', help='Type of log to show, defaults to all', default='all', dest='type', metavar='')
    parser.add_argument('-K', '--key', help='Key to search elasticsearch, this options should be entered with -V or --value argument', dest='key', metavar='')
    parser.add_argument('-V', '--value', help='Value to search elasticsearch, this option should be entered with -K or --key argument', dest='value', metavar='')
    parser.add_argument('--timezone', help='timezone value, defaults to America/New_York', default='America/New_York', dest='timezone', metavar='')
    parser.add_argument('--interval', help='interval value to query elasticsearch in seconds, defaults to 20', default=20, type=int, dest='interval', metavar='')
    parser.add_argument('--run-once', help='Run tail only once and exit', action='store_true', dest='runonce')
    args = parser.parse_args()

    #Function that handles Ctrl+C
    def signal_handler(signal, frame):
        print('Ctrl+C pressed, exiting...')
        sys.exit(0)

    #Function that runs a search with specified parameters
    #TODO: add scroll option to show all logs and not just es_size number of logs
    def elasticsearch_query(es_client,es_index,es_size,query):
        response = es_client.search(index=es_index,sort="@timestamp:asc",size=es_size, body=query)
        return response

    #Function that adds 'must' values to search query
    def add_to_must_query(key,value):
        search_query['query']['bool']['must'].append({"match_phrase": {key: value}},)

    #Function that adds 'should' values to search query
    def add_to_should_query(key,value):
        search_query['query']['bool']['should'].append({"match": {key: value}},)

    ### Main ###

    #Check arguments
    if (not args.hostname) and (not args.key and not args.value):
        parser.print_help()
        print("\nError: elastictail requires at least 1 argument: -H/--hostname or 2 arguments: -K/--key and -V/--value")
        sys.exit(1)

    #Ctrl+C handling
    signal.signal(signal.SIGINT, signal_handler)

    #Initialize elasticsearch
    es_client = Elasticsearch(retry_on_timeout=True)

    #Setting time for search, args.interval seconds ago to now
    time_now_millis = int(round(time() * 1000))
    previous_time = time_now_millis-(args.interval * 1000)

    #Build the query:
    search_query =  {
        "query": {
            "bool": {
                "must": [],
                "minimum_should_match": 1,
                "should": []
            }
        }
    }

    #Build the search query
    #Check if hostname is a list or a string
    if args.hostname:
        if isinstance(args.hostname,list):
            for hostname in args.hostname:
                add_to_should_query('beat.hostname.raw',hostname)
        else:
            add_to_should_query('beat.hostname.raw',args.hostname)


    #Check other arguments
    if args.key and args.value:
        add_to_must_query(args.key, args.value)

    if args.type != 'all':
        add_to_must_query("type", args.type)


    #Add timestamp to search query
    search_query['query']['bool']['must'].insert(0,{"range": {"@timestamp": {"gte": previous_time,"lte": time_now_millis,"format": "epoch_millis"}}})

    while True:
        #Run ES query with current values and search query
        result=elasticsearch_query(es_client,args.index,args.size,search_query)
        #print("Got %d Hits:" % result['hits']['total'])
        for hit in result['hits']['hits']:
            #Naive UTC object
            datetime_obj = datetime.strptime(hit['_source']['@timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
            #Convert to UTC
            datetime_obj_utc = datetime_obj.replace(tzinfo=timezone('UTC'))
            #Convert to args.timezone
            now_timezone = datetime_obj_utc.astimezone(timezone(args.timezone))
            #Convert to String
            now_timezone_string = now_timezone.strftime("%d-%m-%Y %H:%M:%S.%f")[:-3]
            #Handling Unicode messages and encoding it to utf-8
            if not hit['_source']['message']:
                message_final = ''
            elif not isinstance(hit['_source']['message'],list):
                message_final = hit['_source']['message'].encode("utf-8")
            else:
                message_final = hit['_source']['message']
            if 'level' in hit['_source']:
                if hit['_source']['level'].lower() == 'info':
                    level_final = '\033[38;5;036m%s\033[0m' % hit['_source']['level']
                elif hit['_source']['level'].lower() == 'warn':
                    level_final = '\033[38;5;220m%s\033[0m' % hit['_source']['level']
                elif hit['_source']['level'].lower() == 'error':
                    level_final = '\033[38;5;196m%s\033[0m' % hit['_source']['level']
                elif hit['_source']['level'].lower() == 'debug':
                    level_final = '\033[38;5;68m%s\033[0m' % hit['_source']['level']
            else:
                level_final = ''
            print("{t} \033[38;5;104m{host}\033[0m {type} {l}: {m}".format(t=now_timezone_string, m=message_final, l=level_final, **hit["_source"]))

            #If run once options, run one time and exit
            if args.runonce:
                exit(0)

        #Wait args.interval seconds until next search
        sleep(args.interval)
        previous_time = time_now_millis
        time_now_millis = int(round(time() * 1000))
        #Change timestamp
        search_query['query']['bool']['must'][0]['range']['@timestamp']['gte'] = previous_time
        search_query['query']['bool']['must'][0]['range']['@timestamp']['lte'] = time_now_millis

except Exception:
    print "Unexpected error:", sys.exc_info()
    exit(1)
