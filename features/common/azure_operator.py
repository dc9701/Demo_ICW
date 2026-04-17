"""
azure_operator.py.

Description:
This module provides the Azure Operator class, which is used to interact with Azure resources.

Classes:
- AzureOperator: A class to interact with Azure resources.

Functions:
- create_deployment: Create a deployment.
- delete_deployment: Delete a deployment.
- find_deployment: Find a deployment.
- get_deployment_outputs: Get the outputs of a deployment.
- create_resource_group: Create a resource group.
- delete_resource_group: Delete a resource group.
- find_resource_group: Find a resource group.
- get_resource_group_contents: Get the contents of a resource group.
- create_vpc: Create a virtual network.
"""

import os
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode
from common.framework import generate_unique_id, _normalize_template_ids, merge_dicts, save_stack_def_file, update_stack_tags
import logging
import re


# Get the keys and store them in constants
AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
AZURE_SUBSCRIPTION_ID = os.getenv('AZURE_SUBSCRIPTION_ID')
RSA_KEY = os.getenv('RSA_KEY')


class AzureOperator:
    """
    This class represents an Azure Operator.
    """

    def __init__(self, subscription_id: str, tenant_id: str, client_id: str, client_secret: str, region_name: str):
        self.subscription_id = subscription_id
        self.region_name = region_name
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret)
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)

    def create_deployment(
        self,
        deployment_name: str,
        template_spec_id: str = None,
        deployment_template: dict = None,
        deployment_parameters: dict = None,
        tags: dict = None,
        resource_group_name: str = None,
        resource_group_scope: bool = False
    ) -> str:
        """
        Create a deployment at the resource group scope.

        Args:
            resource_group_name (str): The name of the resource group.
            deployment_name (str): The name of the deployment.
            template_spec_id (str, optional): The resource ID of the template spec.
            template_spec_version (str, optional): The version of the template spec.
            deployment_template (dict, optional): The ARM template for the deployment.
            deployment_parameters (dict): The parameters for the deployment.
            tags (dict, optional): Tags to apply to the deployment. Defaults to None.

        Returns:
            str: The name of the deployment.
        """
        # Format parameters as required by Azure SDK
        formatted_parameters = {k: {'value': v} for k, v in deployment_parameters.items()}

        # Build the deployment properties
        deployment_properties = {
            'mode': DeploymentMode.incremental,
            'parameters': formatted_parameters
        }

        if template_spec_id:
            # Use template spec
            deployment_properties['template_link'] = {
                'id': template_spec_id,
            }

        elif deployment_template:
            # Use provided template
            deployment_properties['template'] = deployment_template
        else:
            raise ValueError("Either template_spec_id and template_spec_version or deployment_template must be provided.")

        if tags is None:
            tags = {}  # Default to empty dict if not provided

        if resource_group_scope:
            # Resource Group Scoped Deployment
            deployment_async_operation = self.resource_client.deployments.begin_create_or_update(
                resource_group_name=resource_group_name,
                deployment_name=deployment_name,
                parameters={
                    'properties': deployment_properties,
                    'tags': tags
                }
            )
        else:
            # Subscription Scoped Deployment
            deployment_async_operation = self.resource_client.deployments.begin_create_or_update_at_subscription_scope(
                deployment_name,
                {
                    'location': self.region_name,
                    'properties': deployment_properties,
                    'tags': tags
                }
            )
        deployment_async_operation.wait()

        logging.info(
            f"Deployment '{deployment_name}' created successfully at "
            f"{resource_group_name if resource_group_name else 'subscription'} scope"
        )
        return deployment_name

    def _deploy_stack_on_azure(self, context, parameters, templates, stack_name, deployment_name):
        print(f"Parameters: {parameters}")
        print(f"Templates: {templates}")

        template_spec_ids = _normalize_template_ids(templates)
        # Remove TemplateSpecId param if present
        parameters.pop('TemplateSpecId', None)

        if 'ResourceGroupName' not in parameters and 'name' in parameters:
            parameters['ResourceGroupName'] = parameters['name']

        resource_group_name = parameters.get('ResourceGroupName', None)
        obtained_resource_group_name = resource_group_name

        default_tags = {'Environment': 'Test'}
        final_stack_def = {}

        for i, tpl_id in enumerate(template_spec_ids):

            if i == 0:
                current_resource_group_scope = False
                current_resource_group_name = None
            else:
                current_resource_group_scope = True
                current_resource_group_name = obtained_resource_group_name

            final_stack_def = self._deploy_single_template(
                context, tpl_id, i, template_spec_ids, parameters, deployment_name,
                current_resource_group_name, default_tags, final_stack_def, resource_group_scope=current_resource_group_scope
            )

            if i == 0:
                parameters.pop('ResourceGroupName', None)

            # After first template is deployed, check if we got networkId
            if i == 0 and 'Outputs' in final_stack_def:
                # Initialize variables to store outputs
                network_id = None
                ai_unlimited_ui_access = None

                # Iterate through the Outputs to find 'networkId' and 'aiUnlimitedUiAccess'
                for out in final_stack_def['Outputs']:
                    if out['OutputKey'] == 'networkId':
                        network_id = out['OutputValue']
                    elif out['OutputKey'] == 'aiUnlimitedUiAccess':
                        ai_unlimited_ui_access = out['OutputValue']

                # Process 'networkId' if it exists
                if network_id:
                    match = re.search(r"/resourceGroups/([^/]+)/", network_id)
                    if match:
                        obtained_resource_group_name = match.group(1)
                        logging.info(f"Obtained ResourceGroupName from networkId output: {obtained_resource_group_name}")

                        # Adjust parameters for the second template (jupyter)
                        parameters.pop('AiUnlimitedVersion', None)
                        if 'AiUnlimitedName' in parameters:
                            parameters['NetworkName'] = parameters.pop('AiUnlimitedName')
                        parameters['JupyterToken'] = 'jupyterpass'

                # Process 'aiUnlimitedUiAccess' if it exists
                if ai_unlimited_ui_access:
                    # Remove 'https://' or 'http://' from the URL
                    processed_url = re.sub(r'^https?://', '', ai_unlimited_ui_access)
                    logging.info(f"Processed aiUnlimitedUiAccess URL: {processed_url}")

                    # Store the processed URL in context for later use
                    context.properties.ai_unlimited_ui_access = processed_url

                    # Inject the processed URL into the Jupyter template parameters
                    parameters['AiUnlimitedServerBaseUrl'] = processed_url
                    parameters['AiUnlimitedServerPublicBaseUrl'] = processed_url
                    logging.info(f"Set AiUnlimitedServerBaseUrl to: {processed_url}")
                    logging.info(f"Set AiUnlimitedServerPublicBaseUrl to: {processed_url}")

                    # If first deployment outputs were saved separately, re-append them if missing
                    if hasattr(context.properties, 'first_deployment_outputs'):
                        existing_outputs = {o['OutputKey']: o['OutputValue'] for o in final_stack_def.get('Outputs', [])}
                        for fo in context.properties.first_deployment_outputs:
                            if fo['OutputKey'] not in existing_outputs:
                                final_stack_def['Outputs'].append(fo)

                    if obtained_resource_group_name:
                        context.properties.deployment_name = obtained_resource_group_name

                    # Save updated stack definition file to GitHub.
                    save_stack_def_file(context)
                    logging.info("All templates deployed successfully.")

    def _deploy_single_template(self, context, tpl_id, i, template_spec_ids, parameters, deployment_name, obtained_resource_group_name,
                                default_tags, final_stack_def, resource_group_scope: bool):
        current_deployment_name = deployment_name
        current_parameters = parameters.copy()

        # If your user table had a 'name' param, remove it or rename it as needed
        if 'name' in current_parameters:
            current_deployment_name = current_parameters.pop('name')

        # Decide final RG name
        current_resource_group_name = obtained_resource_group_name if resource_group_scope else None

        logging.info(f"Deploying template {i+1}/{len(template_spec_ids)}: {tpl_id} at "
                     f"{'resource group' if resource_group_scope else 'subscription'} scope "
                     f"{current_resource_group_name if current_resource_group_name else ''}")

        # Deploy current template
        context.azure_operator.create_deployment(
            deployment_name=current_deployment_name,
            template_spec_id=tpl_id,
            deployment_parameters=current_parameters,
            tags=default_tags,
            resource_group_name=current_resource_group_name,
            resource_group_scope=resource_group_scope,
        )
        logging.info(f"Template '{tpl_id}' deployed successfully as '{current_deployment_name}'.")

        # Retrieve deployment details
        deployment = self._get_deployment_details(
            context,
            resource_group_scope,
            current_resource_group_name,
            current_deployment_name
        )
        parameters_list, outputs_list = self._extract_params_and_outputs(deployment)

        rg, tags_list = self._get_tags_from_resource_group(
            context,
            resource_group_scope,
            current_resource_group_name
        )

        stack_def = {
            "StackId": deployment.id,
            "StackName": current_deployment_name,
            "Description": "Azure ARM deployment",
            "Parameters": parameters_list,
            "Outputs": outputs_list,
            "Tags": tags_list,
            "CreationTime": deployment.properties.timestamp.strftime("%Y-%m-%d %H:%M:%S") if deployment.properties.timestamp else "",
            "StackStatus": deployment.properties.provisioning_state,
            "EnableTerminationProtection": False,
            "DriftInformation": {
                "StackDriftStatus": "NOT_CHECKED"
            }
        }

        final_stack_def = merge_dicts(final_stack_def, stack_def)

        aiUnlimitedUiAccess = None
        jupyterUIAccess = None

        if outputs_list:
            for o in outputs_list:
                if o["OutputKey"] == "aiUnlimitedUiAccess":
                    aiUnlimitedUiAccess = o["OutputValue"]
                if o["OutputKey"] == "jupyterUIAccess":
                    jupyterUIAccess = o["OutputValue"]

        # If found, insert them as new tags
        if aiUnlimitedUiAccess:
            final_stack_def.setdefault("Tags", [])
            final_stack_def["Tags"].append({
                "TagKey": "AiUnlimitedWorkspacesURL",
                "TagValue": aiUnlimitedUiAccess
            })

        if jupyterUIAccess:
            final_stack_def.setdefault("Tags", [])

            jupyterUIAccess += "?token=jupyterpass"
            final_stack_def["Tags"].append({
                "TagKey": "AiUnlimitedJupyterURL",
                "TagValue": jupyterUIAccess
            })
        from types import SimpleNamespace
        context.properties.stack = SimpleNamespace(**final_stack_def)

        update_stack_tags(context)
        context.properties.stack_updated = True

        # If this is the first template, store its outputs
        if i == 0 and outputs_list:
            context.properties.first_deployment_outputs = outputs_list.copy()

        return final_stack_def

    def _get_deployment_details(self, context, current_resource_group_scope, current_resource_group_name, current_deployment_name):
        if current_resource_group_scope and current_resource_group_name:
            return context.azure_operator.resource_client.deployments.get(current_resource_group_name, current_deployment_name)
        else:
            return context.azure_operator.get_deployment(current_deployment_name)

    def _extract_params_and_outputs(self, deployment):
        parameters_list = []
        if deployment.properties.parameters:
            for p_name, p_detail in deployment.properties.parameters.items():
                parameters_list.append({
                    "ParameterKey": p_name,
                    "ParameterValue": p_detail.get('value', None)
                })

        outputs_list = []
        if deployment.properties.outputs:
            for o_name, o_detail in deployment.properties.outputs.items():
                outputs_list.append({
                    "OutputKey": o_name,
                    "OutputValue": o_detail.get('value', None)
                })
        return parameters_list, outputs_list

    def _get_tags_from_resource_group(self, context, current_resource_group_scope, current_resource_group_name):
        rg = None
        tags_list = []
        if current_resource_group_scope and current_resource_group_name:
            rg = context.azure_operator.resource_client.resource_groups.get(current_resource_group_name)
            if rg.tags:
                for k, v in rg.tags.items():
                    tags_list.append({"TagKey": k, "TagValue": v})
        return rg, tags_list

    def delete_deployment(self, deployment_name: str):
        """
        Delete a deployment.

        Args:
            deployment_name (str): The name of the deployment.
        """
        self.resource_client.deployments.begin_delete_at_subscription_scope(deployment_name).wait()

        if not self.find_deployment(deployment_name):
            print(f"Deployment {deployment_name} deleted successfully.")

    def find_deployment(self, deployment_name: str) -> bool:
        """
        Find a deployment.

        Args:
            deployment_name (str): The name of the deployment.

        Returns:
            bool: Whether the deployment exists.
        """
        try:
            self.resource_client.deployments.get_at_subscription_scope(deployment_name)
            return True
        except Exception:
            return False

    def get_deployment_outputs(self, deployment_name: str) -> dict:
        """
        Get the outputs of a deployment.

        Args:
            deployment_name (str): The name of the deployment.

        Returns:
            dict: The outputs of the deployment.
        """
        deployment = self.resource_client.deployments.get_at_subscription_scope(deployment_name)
        outputs = deployment.properties.outputs

        return {key: output['value'] for key, output in outputs.items()}

    def create_resource_group(self, rg_name: str):
        """
        Create a resource group.

        Args:
            rg_name (str): The name of the resource group.
        """
        self.resource_client.resource_groups.create_or_update(rg_name, {'location': self.region_name})

        if self.find_resource_group(rg_name):
            print(f"Resource group {rg_name} created successfully.")
        else:
            print(f"Resource group {rg_name} not created.")

    def delete_resource_group(self, context, rg_name: str):
        """
        Delete a resource group.

        Args:
            rg_name (str): The name of the resource group.
        """
        self.resource_client.resource_groups.begin_delete(rg_name).wait()

        if not self.find_resource_group(rg_name):
            print(f"Resource group {rg_name} deleted successfully.")
            # Lastly, remove the stack definition file, local and in GitHub.
            context.properties.stack_updated = False
            git = os.getenv('GIT_PATH', '/usr/bin/git')
            os.system(f"""
                {git} rm ../resources/stacks/{context.properties.stack_name}.json >/dev/null 2>&1
                {git} commit -m 'Removing stack definition file for {context.properties.stack_name}' >/dev/null 2>&1
                {git} push
            """)

    def find_resource_group(self, rg_name: str) -> bool:
        """
        Find a resource group.

        Args:
            rg_name (str): The name of the resource group.

        Returns:
            bool: Whether the resource group exists.
        """
        try:
            self.resource_client.resource_groups.get(rg_name)
            return True
        except Exception:
            return False

    def get_resource_group_contents(self, rg_name: str) -> dict:
        """
        Get the contents of a resource group.

        Args:
            rg_name (str): The name of the resource group.

        Returns:
            dict: The contents of the resource group.
        """
        resource_group = self.resource_client.resource_groups.get(rg_name)
        return resource_group.as_dict()

    def create_vpc(self, vpc_name: str, template: dict, networkCidr: list, subnetCidr: str,
                   tags: list) -> str:
        """
        Create a virtual network.

        Args:
            rg_name (str): The name of the resource group.
            location (str): The location of the resource group.
            template (dict): The ARM template for the virtual network.
            networkCidr (list): The CIDR block for the virtual network.
            subnetCidr (str): The CIDR block for the subnet.
            albSubnetCidr (str): The CIDR block for the ALB subnet.
            deployALBComponents (bool): Whether to deploy the ALB components.
            tags (list): The tags to apply to the resources.

        Returns:
            str: The name of the deployment.
        """
        template['variables']['location'] = self.region_name
        parameters = {
            'name': generate_unique_id(vpc_name),
            'networkCidr': networkCidr,
            'subnetCidr': subnetCidr,
            'Tags': tags
        }

        vpc_arm_deployment_name = self.create_deployment(vpc_name, template, parameters)

        if self.find_deployment(vpc_arm_deployment_name):
            print(f"VPC {vpc_arm_deployment_name} created successfully.")
        else:
            print(f"VPC {vpc_arm_deployment_name} not created.")

        return vpc_arm_deployment_name

    def get_deployment(self, deployment_name: str):
        """
        Get a deployment by name.

        Args:
            deployment_name (str): The name of the deployment.

        Returns:
            The deployment object if found, None otherwise
        """
        try:
            deployment = self.resource_client.deployments.get_at_subscription_scope(deployment_name)
            return deployment
        except Exception as e:
            logging.error(f"Error getting deployment '{deployment_name}': {e}")
            return None
