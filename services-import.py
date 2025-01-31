#!/usr/bin/env python3

import sys
sys.path.append('./cloudsecure_api')

import argparse
import os
import base64
import json
import logging
import signal
import os
import base64
from urllib.request import build_opener, HTTPHandler, Request
import urllib.parse
from cloudsecure import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Call Illumio Cloud API")
    parser.add_argument('--service_account_key', required=True, help="Illumio Service Account Key ID", default=os.environ.get('IllumioCS_ServiceAccountKey'))
    parser.add_argument('--api_url', required=True, help="Illumio API URL", default=os.environ.get('IllumioCS_ApiUrl'))
    parser.add_argument('--tenant_id', required=True, help="Tenant ID", default=os.environ.get('IllumioCS_TenantId'))
    parser.add_argument('--service_account_token', required=True, help="Service Account Token", default=os.environ.get('IllumioCS_ServiceAccountToken'))
    parser.add_argument('--input-file', type=argparse.FileType('r'), required=True, help="Input file")

    args = parser.parse_args()

    service_account_token = args.service_account_token
    if not service_account_token:
        raise ValueError("ServiceAccountToken environment variable is required")

    client = CloudSecureClient(
        url=f'https://{args.api_url}',
        tenant_id=args.tenant_id,
        service_account_key=args.service_account_key,
        service_account_token=args.service_account_token
    )

    ### fetch services first 
    response = client.get('/sec_policy/draft/services')
    data = response.json()

    existing_services = {}
    for svc in data['services']:
        existing_services[svc['name']] = svc['href'] 

    with open(args.input_file.name, 'r') as f:
       services = json.load(f)

    for service in services:
        if 'service_ports' not in service:
            continue

        if existing_services.get(service['name']):
            print(f"Service {service['name']} already exists")
            continue
        else:
            if service['description'] == '':
                service['description'] = 'No description provided'

            data = {
                "name": service['name'],
                "description": service['description'],
                "service_ports": service['service_ports'],
            }

            try:
                print(f'Data: {data}')
                # this posts the iplist to the draft policy
                response = client.post('/sec_policy/draft/services', json=data)
                print(f'Response: {response.status_code} {response.text}')
            except Exception as e:
                print(f'Error: {e}')

if __name__ == "__main__":
    main()
