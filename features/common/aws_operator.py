"""
aws_operator.py.

Description:
This module provides the AWSOperator class, which is used to interact with AWS resources.

Classes:
- AWSOperator: A class to interact with AWS resources.

Functions:
- create_stack: Create a stack.
- delete_stack: Delete a stack.
- get_stack_status: Get the status of a stack.
- get_stack_output: Get the output of a stack.
- get_stack_resources: Get the resources of a stack.
- upload_template_files: Upload template files.
- get_hosted_zone_id: Get the hosted zone id.
- update_route53_record: Update a record in Route53.
- check_and_update_route: Check and update the route.
"""

import os
import boto3
import botocore.exceptions
import json
import re
import time
import logging
import yaml

from common.framework import download_template_files, get_stack_parameters, merge_dicts, save_stack_def_file, update_stack_tags


class AWSOperator:
    """
    This class provides functionality for interacting with AWS services.
    """

    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str, aws_session_token: str = None):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.region_name = region_name

        common_params = {
            'aws_access_key_id': self.aws_access_key_id,
            'aws_secret_access_key': self.aws_secret_access_key
        }

        if self.aws_session_token is not None:
            common_params['aws_session_token'] = self.aws_session_token

        self.aws_cf_connector = boto3.client(service_name='cloudformation',
                                             region_name=self.region_name,
                                             **common_params
                                             )
        self.aws_s3_connector = boto3.client(service_name='s3',
                                             region_name=self.region_name,
                                             **common_params)
        self.aws_ec2_connector = boto3.client(service_name='ec2',
                                              region_name=self.region_name,
                                              **common_params)
        self.aws_ec2_resource = boto3.resource(service_name='ec2',
                                               region_name=self.region_name,
                                               **common_params)
        self.aws_r53_connector = boto3.client(service_name='route53',
                                              **common_params)

    def create_stack(self, deployment_name, template_url=None, deployment_template_body=None, deployment_parameters=None):
        """
        Creates a CloudFormation stack.

        Args:
            deployment_name (str): The name of the deployment.
            template_url (str): The URL of the CloudFormation template.
            deployment_template_body (str): The body of the CloudFormation template.
            deployment_parameters (list): A list of parameters for the template.
        """
        # Ensure the deployment_name is compliant with AWS stack name rules
        deployment_name = deployment_name[:128]  # Max 128 characters

        try:
            params = {
                'StackName': deployment_name,
                'Parameters': deployment_parameters,
                'Capabilities': ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
                'OnFailure': 'DELETE'
            }

            if template_url:
                params['TemplateURL'] = template_url
            elif deployment_template_body:
                # Handle large templates
                template_size = len(deployment_template_body.encode('utf-8'))
                if template_size <= 51200:
                    params['TemplateBody'] = deployment_template_body
                else:
                    # Upload the template to S3
                    bucket_name = 'your-s3-bucket-name'  # Replace with your S3 bucket name
                    template_file_name = f"{deployment_name}.yaml"

                    # Save the template to a local file
                    with open(template_file_name, 'w') as f:
                        f.write(deployment_template_body)

                    # Upload the template file to S3 using your existing function
                    s3_url = self.upload_template_files(file_name=template_file_name, bucket_name=bucket_name)
                    params['TemplateURL'] = s3_url
            else:
                raise ValueError("Either template_url or deployment_template_body must be provided.")

            # Initiate the stack creation
            self.aws_cf_connector.create_stack(**params)
            logging.debug(f"Stack '{deployment_name}' creation initiated.")

            # Wait for stack creation to complete
            waiter = self.aws_cf_connector.get_waiter('stack_create_complete')
            try:
                print(f"Waiting for stack '{deployment_name}' to be created...")
                waiter.wait(StackName=deployment_name, WaiterConfig={'Delay': 60, 'MaxAttempts': 60})
                logging.debug(f"Stack '{deployment_name}' created successfully.")
            except Exception as e:
                logging.error(f"Stack creation failed: {e}")
                raise

        except Exception as e:
            logging.error(f"Failed to create stack '{deployment_name}': {e}")
            raise

    def delete_stack(self, stack_name: str) -> None:
        """Delete a stack in AWS CloudFormation.

        Args:
            stack_name (str): Name of the stack
        """
        self.aws_cf_connector.delete_stack(StackName=stack_name)

        # Wait for stack deletion to complete
        waiter = self.aws_cf_connector.get_waiter('stack_delete_complete')
        try:
            print(f"Waiting for stack '{stack_name}' to be deleted...")
            waiter.wait(StackName=stack_name)
            print(f"Stack '{stack_name}' deleted successfully.")
        except Exception as e:
            error_message = f"Stack deletion failed: {e}"
            print(error_message)
            raise Exception(error_message)

    def _normalize_parameters(self, parameters):
        """
        Take `parameters`, which may be a dict or a list of {"ParameterKey","ParameterValue"} dicts.

        and return a plain dict { key: value, … }.
        """
        if isinstance(parameters, dict):
            return parameters.copy()

        if isinstance(parameters, list):
            out = {}
            for p in parameters:
                if not isinstance(p, dict):
                    continue
                k = p.get("ParameterKey")
                v = p.get("ParameterValue")
                if k is not None and v is not None:
                    out[k] = v
            return out

        raise TypeError(
            f"Unexpected type for parameters: {type(parameters).__name__} (expected dict or list)."
        )

    def _get_template_param_dict(self, context, template):
        """
        Given context and a template (either an S3 URL or a local path).

        call get_stack_parameters(...) and normalize its return to a dict.
        """
        if template.lower().startswith("https:"):
            raw = get_stack_parameters(context, template)
        else:
            full_path = download_template_files('aws', template)
            with open(full_path, 'r') as f:
                if template.lower().endswith(".json"):
                    _body = json.load(f)
                else:
                    _body = yaml.safe_load(f)
            logging.debug(f"Loaded template from {full_path}")
            raw = get_stack_parameters(context, _body)

        # Normalize raw into a plain dict
        if isinstance(raw, dict):
            return raw.copy()
        if isinstance(raw, list):
            return {
                p["ParameterKey"]: p["ParameterValue"]
                for p in raw
                if isinstance(p, dict) and "ParameterKey" in p and "ParameterValue" in p
            }
        raise TypeError(f"get_stack_parameters(...) returned unexpected type: {type(raw).__name__}")

    def _try_create_for_template(self, context, template, stack_name, az, subnet):
        """
        Returns the outputs dict if create_stack succeeded, or raises the underlying exception.
        """
        # Load & normalize raw params for this template
        cur = self._get_template_param_dict(context, template)

        # Only override keys if they exist
        if "AvailabilityZone" in cur:
            cur["AvailabilityZone"] = az
        if "Subnet" in cur:
            cur["Subnet"] = subnet

        # Build the AWS-style Parameter list
        final_list = [
            {"ParameterKey": k, "ParameterValue": str(v)}
            for k, v in cur.items()
        ]

        # Choose deployment name suffix
        name = stack_name
        if 'jupyter-' in template:
            name += '-jup'
        elif 'unlimited' in template:
            name += '-wks'

        # Attempt create_stack()
        try:
            self.create_stack(
                deployment_name=name,
                template_url=(template if template.lower().startswith("https:") else None),
                deployment_template_body=(None if template.lower().startswith("https:") else None),
                deployment_parameters=final_list,
            )
        except botocore.exceptions.WaiterError as we:
            logging.warning(f"WaiterError for template {template} in AZ={az}: {we}")
            raise

        # If no exception, return the outputs
        outs = self.get_stack_output(name)
        return name, outs

    def _attempt_with_az(self, context, templates, stack_name, az, subnet, stack_def):
        """
        For a given AZ/Subnet, attempt each template in `templates`.

          - call _try_create_for_template(...)
          - merge its outputs into stack_def
          - if nested Jupyter, call create_stack(...) directly

        Returns True if any template succeeded (stack_def is mutated); False otherwise.
        """
        for tpl in templates:
            try:
                name_created, outputs = self._try_create_for_template(
                    context, tpl, stack_name, az, subnet
                )
                stack_def.update(merge_dicts(stack_def, self.get_stack_definition(name_created)))

                # If nested Jupyter requested, create it without AZ/Subnet override
                if "CreateJupyterInstance" in outputs:
                    jinfo = self.parse_jupyter_url(outputs["CreateJupyterInstance"])
                    jname = stack_name + "-jup"
                    self.create_stack(
                        deployment_name=jname,
                        template_url=jinfo["template_url"],
                        deployment_parameters=jinfo["deployment_parameters"],
                    )
                    stack_def.update(merge_dicts(stack_def, self.get_stack_definition(jname)))

                return True

            except botocore.exceptions.WaiterError:
                raise

            except botocore.exceptions.ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                msg = e.response.get("Error", {}).get("Message", "")

                # If the template rejected AZ/Subnet injection, retry once without injection
                if code == "ValidationError" and ("[Subnet]" in msg or "[AvailabilityZone]" in msg):
                    logging.warning(
                        f"Template {tpl} refused injected parameter: {msg}. Retrying without AZ/Subnet…"
                    )
                    raw = self._get_template_param_dict(context, tpl)
                    final_list = [
                        {"ParameterKey": k, "ParameterValue": str(v)} for k, v in raw.items()
                    ]
                    jname_root = stack_name + ("-jup" if "jupyter-" in tpl else "-wks")
                    self.create_stack(
                        deployment_name=jname_root,
                        template_url=(tpl if tpl.lower().startswith("https:") else None),
                        deployment_template_body=(None if tpl.lower().startswith("https:") else None),
                        deployment_parameters=final_list,
                    )
                    stack_def.update(merge_dicts(stack_def, self.get_stack_definition(jname_root)))

                    # Nested Jupyter if present
                    outs0 = self.get_stack_output(jname_root)
                    if "CreateJupyterInstance" in outs0:
                        jinfo2 = self.parse_jupyter_url(outs0["CreateJupyterInstance"])
                        jname2 = stack_name + "-jup"
                        self.create_stack(
                            deployment_name=jname2,
                            template_url=jinfo2["template_url"],
                            deployment_parameters=jinfo2["deployment_parameters"],
                        )
                        stack_def.update(merge_dicts(stack_def, self.get_stack_definition(jname2)))
                    return True

                # Otherwise, this entire AZ attempt is fatal for this template; move on
                logging.error(f"ClientError for template {tpl}: {e}")
                continue

            except Exception as exc:
                logging.error(f"Unexpected error for template {tpl} in AZ={az}: {exc}")
                continue

        return False

    def deploy_stack_on_aws(self, context, parameters, templates, stack_name):
        """
        Deploy a new stack in AWS CloudFormation, with fallback to alternate AZ/Subnet combos.
        """
        stack_def = {}
        deployment_successful = False

        # Normalize inbound parameters
        base_params = self._normalize_parameters(parameters)

        # Capture Jupyter password if present
        jpass = (
            base_params.get("JupyterPassword")
            or base_params.get("JupyterToken")
            or base_params.get("jupyterToken")
            or "jupyterpass"
        )

        # Build fallback AZ/Subnet list
        fallback_list = [
            (base_params.get("AvailabilityZone"), base_params.get("Subnet")),
            ("us-west-2b", "subnet-00b86ef2d009313d7"),
            ("us-west-2c", "subnet-0ffa6bedc96f699fa"),
            ("us-west-2d", "subnet-0de853036206a4d96"),
        ]

        # Try each (az_val, subnet_val) until success
        for idx, (az_val, subnet_val) in enumerate(fallback_list):
            try:
                success = self._attempt_with_az(
                    context, templates, stack_name, az_val, subnet_val, stack_def
                )
                if success:
                    deployment_successful = True
                    break

            except botocore.exceptions.WaiterError as we:
                logging.warning(
                    f"AZ={az_val} failed due to capacity (WaiterError). Trying next AZ… {we}"
                )
                continue

        # Final check
        if not deployment_successful:
            raise Exception(
                "All AZ/Subnet fallbacks failed. Stack creation did not succeed."
            )

        # Preserve Jupyter pass, add tags, save definition file
        if jpass:
            context.properties.jupyter_pass = jpass
            for p_dict in stack_def.get("Parameters", []):
                if p_dict.get("ParameterKey") == "JupyterPassword":
                    p_dict["ParameterValue"] = jpass
                    break

            if "Outputs" in stack_def:
                for o_dict in stack_def["Outputs"]:
                    if o_dict.get("OutputKey") == "PublicJupyterUI":
                        stack_def.setdefault("Tags", []).append(
                            {
                                "TagKey": "AiUnlimitedJupyterURL",
                                "TagValue": f"{o_dict['OutputValue']}?token={jpass}",
                            }
                        )

        if "Outputs" in stack_def:
            from types import SimpleNamespace

            context.properties.stack = SimpleNamespace(**stack_def)
            update_stack_tags(context)
            save_stack_def_file(context)
        else:
            logging.warning(
                "Deployment succeeded but no Outputs found; skipping tag updates."
            )

    def does_stack_exist(self, stack_name: str) -> bool:
        """Checks if the specified stack exists.

        Args:
            stack_name (str): Name of the stack

        Returns:
            bool: True if the stack exists, False otherwise
        """
        try:
            self.aws_cf_connector.describe_stacks(StackName=stack_name)
            return True
        except self.aws_cf_connector.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                return False
            else:
                raise

    def get_stack_status(self, stack_name: str) -> str:
        """Get the status of the stack.

        Args:
            stack_name (str): Name of the stack

        Returns:
            str: Status of the stack
        """
        try:
            response = self.aws_cf_connector.describe_stacks(StackName=stack_name)
            return response['Stacks'][0]['StackStatus']
        except botocore.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                return "STACK_NOT_FOUND"
            else:
                raise

    def get_stack_definition(self, stackname: str) -> dict:
        """Get the stack JSON content for the stack definition file.

        Args:
            stackname (str): Name of the stack
        Returns:
            dict: Dictionary with the JSON content of the stack
        """
        response = self.aws_cf_connector.describe_stacks(StackName=stackname)
        return response["Stacks"][0]

    def get_stack_output(self, stackname: str) -> dict:
        """Get the output and resources created of the stack.

        Args:
            stackname (str): Name of the stack
        Returns:
            dict: Dictionary with the output and resources created of the stack
        """
        response = self.aws_cf_connector.describe_stacks(StackName=stackname)
        stack_output_resources = {}
        outputs = response["Stacks"][0]["Outputs"]
        for output in outputs:
            stack_output_resources[output["OutputKey"]] = output["OutputValue"]

        return stack_output_resources

    def get_stack_resources(self, stackname: str) -> dict:
        """Get the resources created of the stack.

        Args:
            stackname (str): Name of the stack
        Returns:
            dict: Dictionary with the resources created of the stack
        """
        response = self.aws_cf_connector.describe_stack_resources(StackName=stackname)
        stack_resources = {}
        resources = response["StackResources"]
        for resource in resources:
            stack_resources[resource["LogicalResourceId"]] = resource["PhysicalResourceId"]

        return stack_resources

    def parse_jupyter_url(self, jupyter_url: str) -> dict:
        """Parse the CreateJupyterInstance URL (AWS) and return dict or parameters required for create_stack().

        Args:
            jupyter_url (str): Name of the stack
        Returns:
            dict: Dictionary with required parameters for AWS create_stack():
                template_url: str
                deployment_parameters: dict[]
        """
        create_stack_dict = {}
        deployment_parameters = []
        exclude_parameters = ['AiUnlimitedAuthPort']
        parsed_url = re.search(r'(.*)\?(.*)\?(.*)', jupyter_url)  # Parse initial jupyter_url into 3 parts.
        params = parsed_url.group(3)
        parsed_params = re.search(r'templateURL=(.*)\&stackName=(.*?)\&(.*)', params)  # Split template_url & param_list.

        for param_str in parsed_params.group(3).split('&'):
            param = re.search(r'param_(.*)=(.*)', param_str)  # Parse key & value.
            param_key = param.group(1)
            param_value = param.group(2)
            if (param_key not in exclude_parameters):
                deployment_parameters.append({'ParameterKey': param_key, 'ParameterValue': param_value})

        # Finally, add default JupyterToken.
        deployment_parameters.append({'ParameterKey': 'JupyterToken', 'ParameterValue': 'jupyterpass'})
        deployment_parameters.append({'ParameterKey': 'VerifyJupyterToken', 'ParameterValue': 'jupyterpass'})

        create_stack_dict['template_url'] = parsed_params.group(1)
        create_stack_dict['deployment_parameters'] = deployment_parameters

        return create_stack_dict

    def upload_template_files(self, file_name: str, bucket_name: str) -> str:
        """
        Uploads a file to an S3 bucket.

        Parameters:
        file_name (str): The name of the file to be uploaded.

        Returns:
        str: The URL of the uploaded file on S3.
        """
        s3_base_dns = f's3-{self.region_name}.amazonaws.com'
        self.aws_s3_connector.upload_file(file_name, bucket_name, file_name)
        uploaded_file_url = f'https://{bucket_name}.{s3_base_dns}/{file_name}'
        os.remove(file_name)
        print('Successfully uploaded file {} to S3 bucket {}'.format(file_name, bucket_name))

        return uploaded_file_url

    def get_hosted_zone_id(self, domain_name: str) -> str:
        """
        Get the hosted zone id of a domain.

        Parameters:
        domain_name (str): The domain name.

        Returns:
        str: The hosted zone id of the domain.
        """
        domain = '.'.join(domain_name.split('.')[1:])

        hosted_zones = self.aws_r53_connector.list_hosted_zones_by_name(DNSName=domain)
        hosted_zone_id = hosted_zones['HostedZones'][0]['Id']

        return hosted_zone_id

    def update_route53_record(self, domain_name: str, record_type: str = 'A', new_value: str = None) -> dict:
        """
        Update a record in Route53.

        Parameters:
        domain_name (str): The domain name.
        record_type (str): The record type.
        new_value (str): The new value of the record.

        Returns:
        dict: The response of the update.
        """
        hosted_zone_id = self.get_hosted_zone_id(domain_name)

        change = {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': domain_name,
                'Type': record_type,
                'TTL': 300,
                'ResourceRecords': [{'Value': new_value}]
            }
        }

        response = self.aws_r53_connector.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={'Changes': [change]}
        )

        return response

    def check_route_change(self, stack_output_resources: str,
                           domain_name: str = 'all-cloud-aut-001.regulus-uat.com') -> bool:
        """
        Check if the route has been updated.

        Parameters:
        domain_name (str): The domain name.
        stack_output_resources (dict): The output of the stack.

        Returns:
        bool: True if the route has been updated, False otherwise.
        """
        hosted_zone_id = self.get_hosted_zone_id(domain_name)
        record_sets = self.aws_r53_connector.list_resource_record_sets(HostedZoneId=hosted_zone_id)
        record_sets = record_sets['ResourceRecordSets']
        for record_set in record_sets:
            if record_set['Name'] == 'all-cloud-aut-001.regulus-uat.com':
                record_value = record_set['ResourceRecords'][0]['Value']
                if record_value == stack_output_resources['PublicIP']:
                    print('Route53 record updated')
                    return True
        return False

    def check_and_update_route(self, domain_name: str, stack_output_resources: dict) -> bool:
        """
        Check if the route has been updated and update it if necessary.

        Parameters:
        domain_name (str): The domain name.
        stack_output_resources (dict): The output of the stack.

        Returns:
        bool: True if the route has been updated, False otherwise.
        """
        counter = 0
        while not self.check_route_change(stack_output_resources, domain_name):
            time.sleep(5)
            counter += 1
            if counter > 5:
                print('Route53 record not updated')
                break
        return True
