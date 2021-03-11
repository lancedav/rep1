#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""Target script for POST requests from Wordpress WPForms plugin. Save in MySQL DB then call GoCardless Flow"""

__author__ = "Dave Tarbatt"
__copyright__ = "Copyright 2017, Dave Tarbatt"
__credits__ = ["Dave Tarbatt", "Simply IP Ltd"]
__license__ = "Proprietary"
__version__ = "1.0.1"
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

# Bits for random string generation
import string
import random

# Pure python connector for MySQL
import pymysql
import pymysql.cursors
#from pymysql import OperationalError

#################### Global Constants ####################

# Script Constants
# Enable Additional Debugging code
DEBUG = 0

# GoCardless Constants
# Environment operating mode; sandbox or live
GC_environment = 'live'

# API Access Token; static string or pull from environment variable os.environ['GC_ACCESS_TOKEN']
GC_accesstoken = 'live_OjFU4Ek91ZHQc7iwX1-vxqM4KFSW53tyuG4E6Ju9'

# Redirect URL; where to go after the GoCardless DD Mandate page
GC_redirecturl = 'https://cp.simplyip.net/code/setup-new-personal-dd-mandate-return.py'

# MySQL DB Vars
# Database Object
dbo = {'dbhost': 'localhost', 'dbname': 'dd_customers', 'username': 'dduser', 'password': 'dduserpass', 'table': 'account'}

#################### Functions ####################

# Generate Random String, default 16 characters long
# random is pseudo-random whereas random.SystemRandom() is better and uses /dev/urandom
def random_string(size=16, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
        return ''.join(random.SystemRandom().choice(chars) for _ in range(size))

#################### Main Program ####################

# Write some HTTP Headers
print("Content-Type: text/html; charset=utf-8")
print("")

# Get the CGI POST data in a multi-dimensional array
form = cgi.FieldStorage()

# Extract the useful form data from the POST. Note that the field order depends on the POST order from WPForms
FirstName = form.getvalue('wpforms[fields][1][first]')
LastName = form.getvalue('wpforms[fields][1][last]')
AddressLineA = form.getvalue('wpforms[fields][2]')
AddressLineB = form.getvalue('wpforms[fields][3]')
AddressCity = form.getvalue('wpforms[fields][4]')
AddressPostCode = form.getvalue('wpforms[fields][5]')
BillingEmail = form.getvalue('wpforms[fields][6]')
FormId = form.getvalue('wpforms[id]')

# If debugging, show some stuff
if (DEBUG == 1) :
        print("FORM START")
        print(form)
        print("FORM END")
        print("")
        print("FORM PART START")
        print("Name %s %s :: AddressLineA %s :: AddressLineB %s :: AddressCity %s :: AddressPostCode %s :: BillingEmail %s :: FormId %s"
                % (FirstName, LastName, AddressLineA, AddressLineB, AddressCity, AddressPostCode, BillingEmail, FormId) )
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

# Generate a session token
SessionToken = random_string()

# Write the start record to the database
try:
        sql = "INSERT INTO account VALUES (%s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, '%s', '%s', %s)" \
                % ('NULL', '', FirstName, LastName, AddressLineA , AddressLineB, AddressCity, AddressPostCode, BillingEmail, 'NULL', 'now()', SessionToken, '', 1)
        if (DEBUG == 1) :
                print("SQL Query: %s" % sql)
        cur = db_conn.cursor()
        cur.execute(sql)
        cur.execute('SELECT LAST_INSERT_ID()')
        rows = cur.fetchall()
        last_id = rows[0]['LAST_INSERT_ID()']
except pymysql.Error as e:
        print("execute() pymysql.Error occurred")
        print(e)
        sys.exit(1)

# If debugging, show some stuff
if (DEBUG == 1) :
        print("OTHER VARS START")
        print("LAST_INSERT_ID() %s"
                % (last_id) )
        print("SessionToken %s"
                % (SessionToken) )
        print("OTHER VARS END")
        print("")

# new GoCardless Client Connection
client = gocardless_pro.Client(
        access_token = GC_accesstoken,
        environment = GC_environment
)

# Create a GoCardless Redirect Flow from the received POST data
redirect_flow = client.redirect_flows.create(
        params={
                "description" : "Managed Internet Services", # This will be shown on the payment pages
                "session_token" : SessionToken, # Not the access token
                "success_redirect_url" : GC_redirecturl,
                "prefilled_customer": {    # Optionally, prefill customer details on the payment page
#                       "company_name": CompanyName,
                        "given_name": FirstName,
                        "family_name": LastName,
                        "email": BillingEmail,
                        "address_line1": AddressLineA,
                        "address_line2": AddressLineB,
                        "city": AddressCity,
                        "postal_code": AddressPostCode
                }
        }
)

# Retrieve the Flow Id and Redirect URL from GoCardless Client Connection
# Hold on to this ID - we'll need it when we
# "confirm" the redirect flow later
RedirectFlowId = redirect_flow.id
RedirectFlowURL = redirect_flow.redirect_url

if (DEBUG == 1) :
        print("RedirectFlowId %s :: RedirectFlowURL %s"
                % (RedirectFlowId, RedirectFlowURL) )

# Update the database record to include the RedirectFlowId
try:
        sql = "UPDATE account SET gc_flow_id='%s', gc_flow_position='%s' WHERE id='%s'" \
                % (redirect_flow.id, 2, last_id)
        if (DEBUG == 1) :
                print("SQL Query: %s" % sql)
        cur = db_conn.cursor()
        cur.execute(sql)
except pymysql.Error as e:
        print("execute() pymysql.Error occurred")
        print(e)
        sys.exit(1)

db_conn.close()

# Do the Redirect to GoCardless
print("<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">")
print("<head><title>Setup New Business DD Mandate (redirect flow)</title>")
print("<meta http-equiv=\"refresh\" content=\"0;URL='%s'\" /></head>" % (RedirectFlowURL) )
print("<body><p>Redirecting to <a href=\"%s\">%s</a></p></body>" % (RedirectFlowURL, RedirectFlowURL) )
print("</html>")
