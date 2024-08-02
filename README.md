# illumio-cs-tools
A set of tools to work with cloudsecure, preliminary CloudSecure SDK and command line utility.

# CloudSecure CLI Utility

`cs.py` is a command-line interface (CLI) tool for interacting with the CloudSecure API. It provides various commands to manage and retrieve information about IP lists, applications, resources, and onboarding processes.

## Installation

Ensure you have Python 3.6+ installed on your system. Then, install the required dependencies:

```bash
pip install click requests pandas tabulate
```

## Configuration

The CLI tool uses environment variables for configuration. Set the following environment variables:

- `IllumioCS_ServiceAccountKey`: Your Illumio Service Account Key ID
- `IllumioCS_ApiUrl`: The Illumio API URL
- `IllumioCS_TenantId`: Your Tenant ID
- `IllumioCS_ServiceAccountToken`: Your Service Account Token

Alternatively, you can provide these values as command-line options.

## Usage

```bash
python cs.py [OPTIONS] COMMAND [ARGS]...
```

### Global Options

- `--verbose`: Enable verbose mode
- `--config FILE`: Path to config file
- `--service_account_key TEXT`: Illumio Service Account Key ID
- `--api_url TEXT`: Illumio API URL
- `--tenant_id TEXT`: Tenant ID
- `--service_account_token TEXT`: Service Account Token
- `--output [table|json|csv]`: Output format (default: table)
- `--pretty`: Pretty print output

### Commands

#### Check Connection

```bash
python cs.py check
```

#### IP Lists

List IP lists:
```bash
python cs.py iplists list
```

#### Applications

List applications:
```bash
python cs.py applications list
```

#### Resources

List resources:
```bash
python cs.py resources list [OPTIONS]
```
Options:
- `--limit INTEGER`: Number of results to return (default: 50)
- `--clouds TEXT`: Comma-separated list of clouds (default: aws)
- `--object_types TEXT`: Comma-separated list of object types
- `--account_ids TEXT`: Comma-separated list of account IDs

List resource object types:
```bash
python cs.py resources objecttypes [OPTIONS]
```
Options:
- `--clouds TEXT`: Comma-separated list of clouds (default: aws)

#### Onboarding

Onboard Azure storage account:
```bash
python cs.py onboarding azure-onboard-storage-account --subscription_id TEXT --storage_account TEXT
```

Onboard AWS S3 bucket:
```bash
python cs.py onboarding aws-onboard-s3-bucket --account-id TEXT --arns TEXT
```

## Examples

List applications in JSON format:
```bash
python cs.py --output json applications list
```

List resources for AWS EC2 instances:
```bash
python cs.py resources list --clouds aws --object_types AWS::EC2::Instance
```

## Troubleshooting

If you encounter any issues, try running the command with the `--verbose` flag for more detailed output. If the problem persists, check your environment variables and ensure you have the necessary permissions to access the CloudSecure API.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Specify the license here]