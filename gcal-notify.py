#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

# Logging purposes ...
def d(msg=None, newline=True):
    if(args.verbose):
        if(msg != None):
            msg = msg.encode('utf-8')

            if newline:
                print(msg)
            else:
                sys.stdout.write(msg)

import sys
import os

import datetime
import dateutil.parser
import argparse
import subprocess
import socket

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

scriptdir = os.path.dirname(os.path.realpath(__file__))

# How many days into the future should we look
rangeDays = 30

recipients = ['user1@domain.tld', 'user2@domain.tld']

# https://developers.google.com/calendar/v3/reference/calendarList/list
# See readme or use Google API Explorer
calendarIds = {
                'Calendar 1 Description':'user@gmail.com',
                'Calendar 2 Description':'uuid@group.calendar.google.com'
                }

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'

parser = argparse.ArgumentParser(description='google-calendar-notify-changes')

parser.add_argument('--dummy', help='Do not send emails', action="store_true", required=False)
parser.add_argument('--calendarId', help='Select calendar to check (overrides hardcoded script settings)', action="store", required=False)
parser.add_argument('--recipient', help='Recipient of email notification (overrides hardcoded script settings)', action="store", required=False)
parser.add_argument('--verbose', help='Print debug information', action="store_true", required=False)

args = parser.parse_args()

if not args.dummy:
    args.dummy = False

if args.calendarId:
    d('Only checking calendar with calendarId ' + args.calendarId + ' as specified on command line')
    calendarIds = {'Calendar provided by CLI':args.calendarId}

if args.recipient:
    d('Only sending notifications to ' + args.recipient + ' as specified on command line')
    recipients = [args.recipient]

store = file.Storage(scriptdir + '/token-readonly.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets(scriptdir + '/credentials.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('calendar', 'v3', http=creds.authorize(Http()))

# 'Z' indicates UTC time
now = datetime.datetime.utcnow()
nowStr = now.isoformat() + 'Z'

delta = datetime.timedelta(days=rangeDays)
then = now + delta
thenStr = then.isoformat() + 'Z'

msg = 'Setting time range from ' + nowStr + ' to ' + thenStr
d(msg)

notifications = []
for calendarPrettyName, calendarId in calendarIds.iteritems():
    d('Checking calendar with ID ' + calendarId + '.')
    events_result = service.events().list(calendarId=calendarId,
                                        timeMin=nowStr,
                                        timeMax=thenStr,
                                        singleEvents=True,
                                        orderBy='startTime',
                                        ).execute()
    events = events_result.get('items', [])

    if not events:
        d('No upcoming events found.')

        continue

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))

        startHelper = dateutil.parser.parse(start)
        startReadable = startHelper.strftime("%A, %B %d, %H:%M") # https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior

        #msg = 'Looking at event "' + event['summary'] + '" taking place on ' + start + '... '
        #print(msg.encode('utf-8'))

        msg = 'Event "' + event['summary'] + '" taking place on ' + startReadable + ' in calendar "' + calendarPrettyName + '" was last updated on ' + event['updated']
        d(msg)

        updated = dateutil.parser.parse(event['updated'])

        # IMPORTANT
        # Uncomment the next three lines for debugging purposes
        #msg = 'Event "' + event['summary'] + '" taking place on ' + startReadable + ' was last updated today at ' + str(updated.strftime("%H:%M"))
        #d(msg)
        #notifications.append(msg)

        if updated.date() != datetime.datetime.today().date():
            msg = 'Event was NOT updated today. Skipping.'
            d(msg)
            continue

        msg = 'Event was updated today. Selecting it for notification.'
        d(msg)

        msg = 'Event "' + event['summary'] + '" taking place on ' + startReadable + ' was created or updated today at ' + str(updated.strftime("%H:%M")) + ' in calendar "' + calendarPrettyName + '"'
        d(msg)

        notifications.append(msg)
        d('Added it to notifications; now containing ' + str(len(notifications)) + ' elements')

if len(notifications) > 0:
    d('Found ' + str(len(notifications)) + ' changes ...')
    #print(notifications)

    changes = "* " + "\n\n* ".join(notifications) + "\n\n-- \nSent by " + __file__ + " on " + socket.gethostname()
    print(changes.encode('utf-8'))

    changesSanitized = changes.replace('"','\\"')
    recipientsOut = ' '.join(recipients)

    cmd = 'echo "' + changesSanitized + '" | mail -a "From: Google Calendar Changes <technical-user@domain.com>" -s "Calendar Updates of Today"  ' + recipientsOut
    d('Command is "' + cmd + '"')

    if not args.dummy:
        d('dummy=false. Sending email notifications.')
        #res = subprocess.getoutput(cmd)
        #res = subprocess.check_output(cmd)
        DEVNULL = open(os.devnull, 'w')
        response = subprocess.call(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)

        d('Response of "' + cmd + '" was ' + str(response))
    else:
        d('dummy=true. Not sending email notifications.')

sys.exit(0)
