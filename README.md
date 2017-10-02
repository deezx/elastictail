# elastictail

Command line tool for tailing logs from elasticsearch

<pre>
optional arguments:
  -h, --help            show this help message and exit
  -I , -index           Index to query, defaults to _all
  -S , --size           Number of results to show, defaults to 1000
  -H [HOST [HOST ...]], --hostname [HOST [HOST ...]]
                        Hostname list
  -T , --type           Type of log to show, defaults to all
  -K , --key            Key to search elasticsearch, this options should be entered with -V or --value argument
  -V , --value          Value to search elasticsearch, this option should be entered with -K or --key argument
  --timezone            timezone value, defaults to America/New_York
  --interval            interval value to query elasticsearch in seconds, defaults to 20
</pre>  
