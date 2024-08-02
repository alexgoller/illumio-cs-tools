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
from illumio import *
from CloudSecure import *

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

    response = client.post('/sec_policy/draft/ip_lists', json=data)
    print(response.json())


if __name__ == "__main__":
    main()
