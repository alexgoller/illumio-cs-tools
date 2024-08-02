#!/usr/bin/env python3
import sys
import click
sys.path.append('./cloudsecure')
import os
import logging
import csv
import json
import pprint
import pandas as pd
from tabulate import tabulate
from io import StringIO
from functools import wraps
from cloudsecure import CloudSecureClient
import requests
from typing import List

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CloudSecureContext:
    def __init__(self):
        self.verbose = False
        self.config = None
        self.service_account_key = None
        self.service_account_token = None
        self.tenant_id = None
        self.api_url = 'cloud.illum.io'
        self.output_format = 'table'
        self.pretty = True

class OutputFormatter:
    @staticmethod
    def flatten_dict(d, parent_key='', sep='_'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if type(v) == dict:
                items.extend(OutputFormatter.flatten_dict(v, new_key, sep=sep).items())
            elif type(v) == list:
                if all(type(i) == dict for i in v):
                    # For lists of dictionaries, we'll just count them
                    items.append((new_key, f"{len(v)} items"))
                else:
                    items.append((new_key, ', '.join(map(str, v))))
            else:
                items.append((new_key, str(v)))
        return dict(items)

    @staticmethod
    def format_output(data, output_format, pretty=False):
        if type(data) == requests.Response:
            try:
                data = data.json()
            except json.JSONDecodeError:
                data = data.text

        if type(data) == str:
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # If it's not JSON, just return it as is
                return data

        if type(data) == dict and len(data) == 1:
            key, value = next(iter(data.items()))
            if isinstance(value, List):
                table_heading = key
                flattened_data = [OutputFormatter.flatten_dict(item) for item in value]
                df = pd.DataFrame(flattened_data)
            else:
                print(f'Found type {type(value)}')

                table_heading = None
                df = pd.DataFrame([OutputFormatter.flatten_dict(data)])
        elif type(data) == list:
            table_heading = None
            flattened_data = [OutputFormatter.flatten_dict(item) for item in data]
            df = pd.DataFrame(flattened_data)
        else:
            table_heading = None
            df = pd.DataFrame([OutputFormatter.flatten_dict(data)])

        if output_format == 'json':
            if pretty:
                return json.dumps(data, indent=2, sort_keys=True)
            else:
                return json.dumps(data)
        elif output_format == 'table':
            table = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
            if table_heading:
                return f"{table_heading}:\n{table}"
            else:
                return table
        elif output_format == 'csv':
            return df.to_csv(index=False)
        else:
            return f"Unsupported output format: {output_format}"

    @staticmethod
    def pretty_print(data, output_format):
        formatted_output = OutputFormatter.format_output(data, output_format, pretty=True)
        click.echo(formatted_output)

def common_options(f):
    @click.option('--verbose', is_flag=True, help='Enable verbose mode.')
    @click.option('--config', type=click.Path(exists=True), help='Path to config file.')
    @click.option('--service_account_key', required=True, help="Illumio Service Account Key ID", 
              default=lambda: os.environ.get('IllumioCS_ServiceAccountKey'), 
              show_default='env var: IllumioCS_ServiceAccountKey')
    @click.option('--api_url', required=True, help="Illumio API URL", 
              default=lambda: os.environ.get('IllumioCS_ApiUrl'), 
              show_default='env var: IllumioCS_ApiUrl')
    @click.option('--tenant_id', required=True, help="Tenant ID", 
              default=lambda: os.environ.get('IllumioCS_TenantId'), 
              show_default='env var: IllumioCS_TenantId')
    @click.option('--service_account_token', required=True, help="Service Account Token", 
              default=lambda: os.environ.get('IllumioCS_ServiceAccountToken'), 
              show_default='env var: IllumioCS_ServiceAccountToken')
    @click.option('--output', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
    @click.option('--pretty', is_flag=True, help='Pretty print output')
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

@click.group()
@common_options
@click.pass_context
def cli(ctx, verbose, config, service_account_key, api_url, tenant_id, service_account_token,output, pretty):
    """Cloud Secure CLI tool"""
    ctx.obj = CloudSecureContext()
    ctx.obj.verbose = verbose
    ctx.obj.config = config
    ctx.obj.service_account_key = service_account_key
    ctx.obj.api_url = api_url
    ctx.obj.tenant_id = tenant_id
    ctx.obj.service_account_token = service_account_token
    ctx.obj.output_format = output
    ctx.obj.pretty = pretty

    ctx.obj.client = CloudSecureClient(
        url=f'https://{api_url}',
        tenant_id=tenant_id,
        service_account_key=service_account_key,
        service_account_token=service_account_token
    )

    if ctx.obj.verbose:
        click.echo(f"Verbose mode is on")
        click.echo(f"Config file: {ctx.obj.config}")
        click.echo(f"Service Account Key: {ctx.obj.service_account_key}")
        click.echo(f"API URL: {ctx.obj.api_url}")
        click.echo(f"Tenant ID: {ctx.obj.tenant_id}")
        click.echo(f"Service Account Token: {ctx.obj.service_account_token}")

@cli.command()
@click.pass_context
def check(ctx):
    """Check connection"""
    client = ctx.obj.client
    click.echo("Checking connection...")
    response = client.get('/noop')
    if response.status_code == 200:
        click.echo("Connection successful")

@cli.group()
@click.pass_context
def iplists(ctx):
    """IP list operations"""
    pass


@cli.group()
@click.pass_context
def onboarding(ctx):
    """Onboarding operations"""
    pass

@cli.group()
@click.pass_context
def applications(ctx):
    """Applications operations"""
    pass

@cli.group()
@click.pass_context
def resources(ctx):
    """Resource operations"""
    pass

@onboarding.command()
@click.pass_context
@click.option('--subscription_id', required=True, help='Subscription ID')
@click.option('--storage_account', required=True, help='Storage Account Name')
def azure_onboard_storage_account(ctx, subscription_id, storage_account):
    """Onboard storage"""
    client = ctx.obj.client
    click.echo("Onboarding storage...")
    destinations = [storage_account]
    endpoint = f'/integrations/cloud_credentials'
    data = {
        "subscription_id": subscription_id,
        "type": "AzureFlow",
        "destinations": destinations
    }
    try:
        response = client.post(endpoint, json=data)
        if response.status_code == 200:
            click.echo(f'Successfully onboarded storage account {storage_account} on subscription {subscription_id}')
        else:
            click.echo(f'Failed to onboard storage account {storage_account} on subscription {subscription_id}')
            click.echo(response.text)
    except Exception as e:
        click.echo(f'Exception onboarding storage account {storage_account} on subscription {subscription_id}')
        click.echo(str(e))

@onboarding.command()
@click.pass_context
@click.option('--account-id', required=True, help='Subscription ID')
@click.option('--arns', required=True, help='Comma separated list of S3 bucket ARNs for onboarding')
def aws_onboard_s3_bucket(ctx, org_id, arn):
    """Onboard S3 bucket"""
    client = ctx.obj.client
    click.echo("Onboarding S3 bucket...")
    endpoint = f'/integrations/cloud_credentials'
    data = {
        "org_id": org_id,
        "type": "AWSFlow",
        "destinations": [ arns.split(',') ]
    }
    try:
        response = client.post(endpoint, json=data)
        if response.status_code == 200:
            click.echo(f'Successfully onboarded S3 bucket {destinations} on org {org_id}')
        else:
            click.echo(f'Failed to onboard S3 bucket {destinations} on org {org_id}')
            click.echo(response.text)
    except Exception as e:
        click.echo(f'Exception onboarding S3 bucket {destinations} on org {org_id}')
        click.echo(str(e))

@onboarding.command()
@click.pass_context
@click.option('--subscription_id', required=True, help='Subscription ID')
@click.option('--storage_account', required=True, help='Storage Account Name')
def azure_onboard_storage_account(ctx, subscription_id, storage_account):
    """Onboard storage"""
    client = ctx.obj.client
    click.echo("Onboarding storage...")
    destinations = [storage_account]
    endpoint = f'/integrations/cloud_credentials'
    data = {
        "subscription_id": subscription_id,
        "type": "AzureFlow",
        "destinations": destinations
    }
    try:
        response = client.post(endpoint, json=data)
        if response.status_code == 200:
            click.echo(f'Successfully onboarded storage account {storage_account} on subscription {subscription_id}')
        else:
            click.echo(f'Failed to onboard storage account {storage_account} on subscription {subscription_id}')
            click.echo(response.text)
    except Exception as e:
        click.echo(f'Exception onboarding storage account {storage_account} on subscription {subscription_id}')
        click.echo(str(e))

@applications.command()
@click.pass_context
def list(ctx):
    """List applications"""
    client = ctx.obj.client
    click.echo("Listing applications...")
    response = client.get('/applications')
    rdata = response.json()
    output = OutputFormatter.format_output(response.json(), ctx.obj.output_format)
    click.echo(output)

@resources.command()
@click.option('--limit', type=int, required=False, help='Resource name', default=50)
@click.option('--clouds', type=str, required=False, help='Resource name', default='aws')
@click.option('--object_types', type=str, required=False, help='Resource name')
@click.option('--account_ids', type=str, required=False, help='Account IDs')
@click.pass_context
def list(ctx, limit, clouds, object_types, account_ids):
    """List resources"""
    payload = {
        "max_results":limit,
        "sortBy": {
            "asc": True,
            "field":"STATE"
        }
    }
    if clouds:
        clouds = clouds.split(',')
        payload['clouds'] = clouds
    
    if object_types:
        object_types = object_types.split(',')
        payload['object_types'] = object_types

    if account_ids:
        account_ids = account_ids.split(',')
        payload['account_ids'] = account_ids

    logging.debug("Sending payload: %s", payload)

    client = ctx.obj.client
    click.echo("Listing resources...")
    response = client.post('/bridge/resources', json=payload)
    print(response.json())
    output = OutputFormatter.format_output(response.json(), ctx.obj.output_format)
    click.echo(output)

### {"clouds":["aws"],"object_types":["AWS::EC2::Instance"],"max_results":50,"sortBy":{"asc":true,"field":"STATE"}}
@resources.command()
@click.option('--clouds', type=str, required=False, help='Resource name', default='aws')
@click.pass_context
def objecttypes(ctx, clouds):
    """List resource object types"""
    payload = {
        "clouds": clouds,
        "metadata_type": "OBJECTTYPE"
    }
    client = ctx.obj.client
    click.echo("Listing resource object types...")
    response = client.get('/inventory/metadata', params=payload)
    if ctx.obj.pretty:
        OutputFormatter.pretty_print(response.json(), ctx.obj.output_format)
    else:
        output = OutputFormatter.format_output(response.json(), ctx.obj.output_format)
        click.echo(output)
    print(type(output))
    # print(response.text)
    # rdata = response.json()
    # print(rdata)

@iplists.command()
@click.pass_context
def list(ctx):
    """List IP lists"""
    client = ctx.obj.client
    click.echo("Listing IP lists...")
    response = client.get('/sec_policy/active/ip_lists')
    rdata = response.json()
    output = OutputFormatter.format_output(response.json(), ctx.obj.output_format)
    click.echo(output)
    # for iplists in rdata['ip_lists']:
    #     click.echo(iplists)


def main():
    logging.debug("Hello")

if __name__ == "__main__":
    cli()
    main()
