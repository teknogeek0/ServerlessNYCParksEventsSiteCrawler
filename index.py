#!/usr/bin/env python

# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

##import required libraries
import json
from datetime import datetime, timedelta
import boto3
import os
import requests
import re
import math
from bs4 import BeautifulSoup

## Set up our DDB connection. Will use a default table that needs to be created outside of the function
DYNAMODB = boto3.resource('dynamodb')
if 'DDB_TABLE' in os.environ and os.environ['DDB_TABLE'] != '':
    print("Found DDB_TABLE: "+str(os.environ['DDB_TABLE']))
    MYTABLE = DYNAMODB.Table(os.environ['DDB_TABLE'])
else:
    print("ERROR: Unable to find DynamoDB table in Environment Variables, defaulting to EventsTable-Demo")
    MYTABLE = DYNAMODB.Table('EventsTable-Demo')

## Get the number of days of events to process
if 'CRAWLER_DAYS' in os.environ and os.environ['CRAWLER_DAYS'] != '':
    print("Found CRAWLER_DAYS: "+str(os.environ['CRAWLER_DAYS']))
    CRAWLER_DAYS = int(os.environ['CRAWLER_DAYS'])
else:
    print("ERROR: Unable to find the number of days to crawl in Environment Variables, defaulting to 7")
    CRAWLER_DAYS = 7

## constants
HEADERS = {'User-Agent': "Example crawler script that parses events from NYC Parks Events site, no malicious intent"}
TODAY=datetime.today().strftime('%Y-%m-%d')

TODAY_PLUS=(datetime.today()+timedelta(days=CRAWLER_DAYS)).strftime('%Y-%m-%d')
URL = 'https://www.nycgovparks.org/events'
PAGE_URL=URL+"/f"+TODAY+"/t"+TODAY_PLUS
ALL_EVENTS_IDENTIFIER = 'events_leftcol'
EACH_EVENT_IDENTIFIER = 'http://schema.org/Event'

## used to help figure out the number of pages to crawl
def roundup(x):
    return int(math.ceil(x / 10.0)) * 10

## Crawls the intial search results page and determines based on the number of overall results the number
## of pages that it will need to parse
def getPages():
    print("INFO: Trying to read: "+PAGE_URL)
    page = requests.get(PAGE_URL, headers=HEADERS)
    content = BeautifulSoup(page.content, 'html.parser')
    alert_content = content.find('p', {'class': "alert"}).get_text()
    total_events = re.search('out of ([0-9,]*) events', alert_content)
    print("INFO: Found "+str(total_events.group(1).replace(',', ''))+" events listed")
    total_pages = roundup(int(total_events.group(1).replace(',', ''))) / 10
    return total_pages

## Get all of the events from a given page identified by the passed in page_counter
def getAllEvents(page_counter):
    all_events_list = {}
    ## get the page
    page = requests.get(PAGE_URL+'/p'+str(page_counter), headers=HEADERS)
    content = BeautifulSoup(page.content, 'html.parser')
    all_events = content.find('div', {'id': ALL_EVENTS_IDENTIFIER})
    ## grab event
    all_events_list = all_events.find_all('div', {'itemtype': EACH_EVENT_IDENTIFIER})
    ##print (all_events_list[1].prettify())
    return all_events_list

## parse out all of the event details from a given page's events
def parseEvents(all_events_list):
    event_info={}
    all_events_details=[]
    event_categories=[]

    for counter in range(len(all_events_list)):
        event_info['month'] = all_events_list[counter].find('span', {'class': 'cal_month'}).get_text()
        event_info['day'] = all_events_list[counter].find('span', {'class': 'cal_day'}).get_text()
        event_info['location'] = all_events_list[counter].find('span', {'itemprop': 'name'}).get_text()
        event_info['name'] = all_events_list[counter].find('h3', {'itemprop': 'name'}).get_text()
        name_item = all_events_list[counter].find('h3', {'itemprop': 'name'}).findChildren()
        event_info['startDate'] = all_events_list[counter].find('meta', {'itemprop': 'startDate'}).attrs['content']
        event_info['endDate'] = all_events_list[counter].find('meta', {'itemprop': 'endDate'}).attrs['content']
        event_info['id'] = name_item[0].attrs['href']

        ## The below represent attributes that might be missing from events and need to be defaulted to null otherwise
        if all_events_list[counter].find('span', {'itemprop': 'addressLocality'}):
            event_info['borough'] = all_events_list[counter].find('span', {'itemprop': 'addressLocality'}).get_text()
        else:
            event_info['borough'] = 'null'
        if all_events_list[counter].find('meta', {'itemprop': 'streetAddress'}):
            event_info['streetAddress'] = all_events_list[counter].find('meta', {'itemprop': 'streetAddress'}).attrs['content']
        else:
            event_info['streetAddress'] = 'null'
        if all_events_list[counter].find('span', {'itemprop': 'description'}).get_text():
            event_info['description'] = all_events_list[counter].find('span', {'itemprop': 'description'}).get_text()
        else:
            event_info['description'] = 'null'
        if all_events_list[counter].find_all('span', {'class': None, 'itemprop' : None}):
            span_events = all_events_list[counter].find_all('span', {'class': None, 'itemprop' : None})
            for span_counter in range(len(span_events)):
                event_categories.append(span_events[span_counter].get_text())

            event_info['categories'] = event_categories
        else:
            event_info['categories'] = 'null'
        #print json.dumps(event_info, indent=4, sort_keys=True)
        all_events_details.append(event_info)
        ##the following weren't taking the new data in this loop, so forcefully clear it here. i'm not understanding
        ## something about python var scope ;)
        event_info={}
        span_events={}
        event_categories=[]

    return all_events_details

## Store in DynamoDB the results of our parsed event data
def ddbWriter(all_events_details):
    with MYTABLE.batch_writer() as batch:
        item_counter=0
        while item_counter<len(all_events_details):
            item=all_events_details[item_counter]
            ##For Debugging: print json.dumps(item, indent=4, sort_keys=True)
            batch.put_item(
                Item=item
            )
            item_counter +=1

## Lambda handler
def handler(event, context):
    total_pages = getPages()
    page_counter=1
    while page_counter <= total_pages:
        all_events_list = getAllEvents(page_counter)
        all_events_details = parseEvents(all_events_list)
        ddbWriter(all_events_details)
        all_events_details = {}
        all_events_list = {}
        page_counter+=1

    return("Success! Parsed Events")
