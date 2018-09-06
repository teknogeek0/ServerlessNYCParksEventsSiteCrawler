NYC Parks Event Crawler
==============================================

This AWS Serverless Application crawls the NYC Parks's Events website (https://www.nycgovparks.org/events/) and generates a scoped view of the data listed there and stores it in an Amazon DynamoDB Table.

This application was created as part of a demo for the "Build on Serverless | Alexa and Serverless Apps - How to Hack for Good" Twitch event: https://www.twitch.tv/events/_io6UwgXSb2YhlQ3rKgWPw

NOTE: Per the license this code is meant as an example and carries no warranty. Please learn from it!

How does it work?
-----------
This code makes use of the BeautifulSoup https://www.crummy.com/software/BeautifulSoup/ package to digest the HTML content of a website and make it available as an object that can be parsed in Python. The code then looks for specific records from the page processed and creates a JSON structure that can be inserted into DynamoDB.

The code is executed as part of an AWS Lambda function (https://aws.amazon.com/lambda) which can be triggered manually or on a schedule if so desired. The Lambda function can be deployed via AWS Serverless Application Model (AWS SAM) templates (see template.yml).

Number of days of events to crawl
-----------
The application is meant to crawl a number of days worth of events to process. By default this is set to 7 days in the AWS SAM template via the envrionment variable "CRAWLER_DAYS". You can tune this manually in that file, but note that increasing it can increase the time it takes the Lambda function to process which could cause an execution timeout. Tune the "Timeout" attribute accordingly if this occurs.

External dependencies
-----------
This application makes use of a few 3rd party external dependencies:
* boto3 - https://github.com/boto/boto3
* requests - https://github.com/requests/requests
* BeautifulSoup - https://code.launchpad.net/beautifulsoup

To install the dependencies, run the following command in the root directory of the code:
```bash
pip install -r requirements.txt -t ./
```

Deploying the Application
-----------
There are two primary ways to deploy this application:
1. Use the AWS SAM CLI - https://github.com/awslabs/aws-sam-cli
1. Deploy via the AWS Serverless Application repository: https://aws.amazon.com/serverless/serverlessrepo/

==============================================

Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0