#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""Target script for POST requests/return from GoCardless Flow API. Save in MySQL DB then e-mail New Setup Notification"""

__author__ = "Dave Tarbatt"
__copyright__ = "Copyright 2017, Dave Tarbatt"
__credits__ = ["Dave Tarbatt", "Simply IP Ltd"]
__license__ = "Proprietary"
__version__ = "1.0.2"
__maintainer__ = "Dave Tarbatt"
__email__ = "dave@simplyip.net"
__status__ = "Production"

# System functions, e.g. sys.exit
import sys

# enable debugging
import cgitb
# CGI Traceback Manager (do not enable in production)
cgitb.enable()

# Necessary bits for parsing POST
import cgi

# Necessary bits for GoCardless
import os
import gocardless_pro

# Pure python connector for MySQL
import pymysql
import pymysql.cursors

#################### Global Constants ####################

# Script Constants
# Enable Additional Debugging code
DEBUG = 0

# GoCardless Constants
# Environment operating mode; sandbox or live
GC_environment = 'live'

# API Access Token; static string or pull from environment variable os.environ['GC_ACCESS_TOKEN']
GC_accesstoken = 'live_OjFU4Ek91ZHQc7iwX1-vxqM4KFSW53tyuG4E6Ju9'

# Redirect URL; where to go after this script finishes
SetupCompleteURL = 'https://cp.linkipnetworks.co.uk/index.php/setup-complete/'

# MySQL DB Vars
# Database Object
dbo = {'dbhost': 'localhost', 'dbname': 'dd_customers', 'username': 'dduser', 'password': 'dduserpass', 'table': 'account'}

#################### Functions ####################

#

#################### Main Program ####################

# Write some HTTP Headers
print("Content-Type: text/html; charset=utf-8")
print("")

# Get the CGI POST data in a multi-dimensional array
form = cgi.FieldStorage()

# Extract the useful form data from the POST. Note that the field order depends on the POST order from WPForms
RedirectFlowId = form.getvalue('redirect_flow_id')

# If debugging, show some stuff
if (DEBUG == 1) :
        print("FORM START")
        print(form)
        print("FORM END")
        print("")
        print("FORM PART START")
        print("RedirectFlowId %s"
                % (RedirectFlowId) )
        print(RedirectFlowId)
        print("FORM PART END")
        print("")

# Connect to the local database
try:
        db_conn = pymysql.connect(
                host=dbo['dbhost'],
                user=dbo['username'],
                password=dbo['password'],
                db=dbo['dbname'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor)
except pymysql.Error as e:
        print("connect() pymysql.Error occurrred")
        print(e)
        sys.exit(1)

# Update the database record; set gc_flow_position and last_update for the related RedirectFlowId
try:
        sql = "UPDATE account SET last_update=%s, gc_flow_position='%s' WHERE gc_flow_id='%s'" \
                % ('now()', 3, RedirectFlowId)
        if (DEBUG == 1) :
                print("SQL Query: %s" % sql)
        cur = db_conn.cursor()
        cur.execute(sql)
except pymysql.Error as e:
        print("execute() pymysql.Error occurred")
        print(e)
        sys.exit(1)

# Get the gc_session_token back from the database
try:
        sql = "SELECT gc_session_token FROM account WHERE gc_flow_id='%s'" \
                % (RedirectFlowId)
        if (DEBUG == 1) :
                print("SQL Query: %s" % sql)
        cur = db_conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        GCSessionToken = rows[0]['gc_session_token']
except pymysql.Error as e:
        print("execute() pymysql.Error occurred")
        print(e)
        sys.exit(1)

# new GoCardless Client Connection - To Complete the flow
client = gocardless_pro.Client(
        access_token = GC_accesstoken,
        environment = GC_environment
)

# GoCardless complete() the flow
redirect_flow = client.redirect_flows.complete(
        RedirectFlowId, # The redirect flow ID from above.
        params={
                "session_token": GCSessionToken
        }
)

# Update the database record; set gc_flow_position and creation_date for the related RedirectFlowId
try:
        sql = "UPDATE account SET creation_date=%s, last_update=%s, gc_flow_position='%s' WHERE gc_flow_id='%s'" \
                % ('now()', 'now()', 4, RedirectFlowId)
        if (DEBUG == 1) :
                print("SQL Query: %s" % sql)
        cur = db_conn.cursor()
        cur.execute(sql)
except pymysql.Error as e:
        print("execute() pymysql.Error occurred")
        print(e)
        sys.exit(1)

db_conn.close()

# Send an e-mail
## ToDo

# Do the Redirect back to the Simply IP Control Panel
print("<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">")
print("<head><title>Setup New Business DD Mandate (return flow)</title>")
print("<meta http-equiv=\"refresh\" content=\"0;URL='%s'\" /></head>" % (SetupCompleteURL) )
print("<body><p>Redirecting to <a href=\"%s\">%s</a></p></body>" % (SetupCompleteURL, SetupCompleteURL) )
print("</html>")
