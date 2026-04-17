"""
stack_steps.py.

Description: This module contains the step definitions for the stack.feature file.
"""

from behave import then, when
from datetime import datetime
import json
import logging
import os
from types import SimpleNamespace

from common.framework import generate_unique_id, get_property, get_stack_parameters, get_stack_templates, set_test_result, update_stack_tags
from common.framework import download_marketplace_template, save_stack_def_file

# 'WHEN ...' STEPS:


@when('I check the existence of the resource group "{rg_name}"')
def step_when_check_resource_group_exists(context, rg_name):
    """
    Checks if the specified resource group exists.

    Args:
        context: Behave context object.
        rg_name: The name of the resource group to check.
    """
    # Evaluate the resource group name expression
    rg_name = get_property(context, rg_name)
    logging.debug(f"Checking existence of resource group '{rg_name}'")
    context.rg_exists = context.azure_operator.find_resource_group(rg_name)


@when('I check the existence of the stack "{stack_name_expr}"')
def step_when_check_stack_exists(context, stack_name_expr):
    """
    Checks if the specified AWS CloudFormation stack exists.
    """
    stack_name = get_property(context, stack_name_expr)
    logging.debug(f"Checking existence of stack '{stack_name}'")
    context.stack_exists = context.aws_operator.does_stack_exist(stack_name)


@when('I delete the deployment "{deployment_name}"')
def step_when_delete_deployment(context, deployment_name):
    """
    Deletes the specified deployment.

    Args:
        context: Behave context object.
        deployment_name: The name of the deployment to delete. Can be a string literal or a 'context.*' variable.
    """
    try:
        deployment_name = get_property(context, deployment_name)
        context.azure_operator.delete_deployment(deployment_name)
        print(f"Deployment '{deployment_name}' deleted successfully.")
    except Exception as e:
        logging.error(f"Error deleting deployment '{deployment_name}': {e}")
        raise


@when('I delete the resource group "{rg_name}"')
def step_when_delete_resource_group(context, rg_name):
    """
    Deletes the specified resource group.

    Args:
        context: Behave context object.
        rg_name: The name of the resource group to delete. Can be a string literal or a 'context.*' variable.
    """
    try:
        rg_name = get_property(context, rg_name)
        context.azure_operator.delete_resource_group(context, rg_name)
        print(f"Resource group '{rg_name}' deleted successfully.")
    except Exception as e:
        logging.error(f"Error deleting resource group '{rg_name}': {e}")
        raise


@when('I delete the stack "{stack_name_expr}"')
def step_when_delete_stack(context, stack_name_expr):
    """
    Deletes the specified AWS CloudFormation stack.
    """
    stack_name = get_property(context, stack_name_expr)
    logging.debug(f"Deleting stack '{stack_name}'")

    try:
        context.aws_operator.delete_stack(stack_name)
        logging.info(f"Stack '{stack_name}' deletion initiated successfully.")

        if '-wks' in stack_name:  # Remove stack definition file if removing workspaces stack (last one)
            context.properties.stack_updated = False
            stack_name = stack_name.replace('-wks', '')  # Strip the trailing '-wks'.
            git = os.getenv('GIT_PATH', '/usr/bin/git')
            os.system(f"""
                {git} rm ../resources/stacks/{stack_name}.json >/dev/null 2>&1
                {git} commit -m 'Removing stack definition file for {context.properties.stack_name}' >/dev/null 2>&1
                {git} push
            """)

    except Exception as e:
        logging.error(f"Error deleting stack '{stack_name}': {e}")
        raise


@when('I deploy a new stack with')
def step_when_deploy_new_stack(context):
    """
    Deploys a new stack using the specified parameters.

    Args:
        context: Behave context object containing deployment parameters and template information.
    """
    parameters = get_stack_parameters(context)
    context.properties.deployment_parameters = parameters
    templates = get_stack_templates(context)

    print(f"Templates: {templates}")

    # Determine stack name
    stack_name = parameters.get('name') or parameters.get('stack_name') or context.properties.stack_name
    if not stack_name:
        stack_name = parameters.get('ResourceGroupName') or 'uat-azure-eastus-nolb'
        context.properties.stack_name = stack_name

    deployment_name = stack_name
    context.properties.deployment_name = deployment_name

    # Ensure cloud provider is set
    cloud_provider = getattr(context.properties, 'cloud', None)
    if not cloud_provider:
        raise ValueError("Cloud provider not specified in context.properties.cloud")
    cloud_provider = cloud_provider.lower()
    logging.info(f"Deploying stack on cloud provider: {cloud_provider}")

    if cloud_provider == 'azure':
        # TODO: REGULUS-1969 - Move AZ-MKT code from stack_steps.py to azure_operator.py
        if 'Marketplace' in parameters and 'MarketplaceOffer' in parameters:
            if 'ResourceGroupName' not in parameters and 'name' in parameters:
                parameters['ResourceGroupName'] = parameters['name']
            rg_name = parameters.get('ResourceGroupName')
            if not context.azure_operator.find_resource_group(rg_name):
                logging.info(f"Resource group '{rg_name} does not exist. Creating it now...")
                context.azure_operator.create_resource_group(rg_name)
            else:
                logging.info(f"Resource group '{rg_name}' already exists.")

            github_token = os.getenv('GITHUB_TOKEN')
            # Use your download function to get the template file from GitHub
            template_file = download_marketplace_template(
                platform='azure',
                template_type='marketplace',
                github_token=github_token
            )
            with open(template_file, 'r') as f:
                deployment_template = json.load(f)
            # Remove these keys so they aren’t processed later
            parameters.pop('Marketplace', None)
            parameters.pop('MarketplaceOffer', None)
            parameters.pop('AiUnlimitedName', None)
            resource_group_name = parameters.pop('ResourceGroupName', None)
            parameters.pop('name', None)

            context.azure_operator.create_deployment(
                deployment_name=deployment_name,
                deployment_template=deployment_template,
                deployment_parameters=parameters,
                tags={"Environment": "Test"},
                resource_group_name=resource_group_name,
                resource_group_scope=True
            )

            # Retrieve the deployment details
            deployment = context.azure_operator.resource_client.deployments.get(resource_group_name, deployment_name)
            if deployment is None:
                logging.error("Marketplace deployment did not return a valid deployment object.")
            else:
                # Extract parameters and outputs using helper function
                params_list, outputs_list = context.azure_operator._extract_params_and_outputs(deployment)

                # Build a stack definition similar to what _deploy_single_template does:
                stack_def = {
                    "StackId": deployment.id,
                    "StackName": deployment_name,
                    "Description": "Azure ARM deployment",
                    "Parameters": params_list,
                    "Outputs": outputs_list,
                    "Tags": [{"TagKey": "ProjectUserName", "TagValue": "TDUSER"}] if context.properties.marketplace else [],
                    "CreationTime": deployment.properties.timestamp.strftime("%Y-%m-%d %H:%M:%S") if deployment.properties.timestamp else "",
                    "StackStatus": deployment.properties.provisioning_state,
                    "EnableTerminationProtection": False,
                    "DriftInformation": {
                        "StackDriftStatus": "NOT_CHECKED"
                    }
                }

                # Use jupyterPassword parameter, if specified
                jupyter_pass = parameters.get("JupyterPassword") or parameters.get("JupyterToken") or parameters.get("jupyterToken") or 'jupyterpass'
                context.properties.jupyter_pass = jupyter_pass

                for o in outputs_list:
                    if o["OutputKey"] == "publicJupyterUI":
                        stack_def["Tags"].append({
                            "TagKey": "AiUnlimitedJupyterURL",
                            "TagValue": o["OutputValue"] + "?token=" + jupyter_pass
                        })

                # Update context.properties.stack using a SimpleNamespace
                from types import SimpleNamespace
                context.properties.stack = SimpleNamespace(**stack_def)

                print(f"Context_properties = {context.properties.stack}")

                # Finally, save the stack definition file
                save_stack_def_file(context)
                logging.info("Marketplace deployment: Stack definition file saved successfully.")
        else:
            context.azure_operator._deploy_stack_on_azure(context, parameters, templates, stack_name, deployment_name)
    elif cloud_provider == 'aws':
        context.aws_operator.deploy_stack_on_aws(context, parameters, templates, stack_name)
    else:
        raise ValueError(f"Unsupported cloud provider: {cloud_provider}")


@when('I generate the stack name following the naming convention')
def step_when_generate_stack_name(context):
    """
    Generates a stack name following the specified naming convention.
    """
    # Get current timestamp for temporary stacks if releases are not specified
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')

    # Build the stack name components
    cloud = context.properties.cloud
    region = context.properties.region_name.replace('-', '')
    template = context.properties.template_type
    network_type = context.properties.network_type
    releases = context.properties.releases or timestamp

    # Construct the stack name
    stack_name = f"aiu-test-{cloud}-{region}-{template}"
    if network_type:
        stack_name += f"-{network_type}"
    if releases:
        stack_name += f"-{releases}"

    # Limit stack name to acceptable lengths (AWS limit is 128 characters)
    max_length = 128
    if len(stack_name) > max_length:
        stack_name = stack_name[:max_length]

    context.properties.stack_name = stack_name
    logging.debug(f"Generated stack_name: {context.properties.stack_name}")


@when('I generate a unique stack name')
def step_when_generate_unique_stack_name(context):
    """
    Generates a unique stack name and stores it in the context properties.

    Args:
        context: Behave context object.
    """
    context.properties.stack_name = generate_unique_id('ai-unlimited-resgrp_')
    logging.debug(f"Generated stack_name: {context.properties.stack_name}")


@when('I get the contents of the resource group "{rg_name_expr}"')
def step_when_get_resource_group_contents(context, rg_name_expr):
    """
    Retrieves the contents of the specified resource group.

    Args:
        context: Behave context object.
        rg_name_expr: The name of the resource group to retrieve contents from.
    """
    rg_name = get_property(context, rg_name_expr)
    logging.debug(f"Listing resources in resource group'{rg_name}'")
    context.rg_contents = context.azure_operator.get_resource_group_contents(rg_name)


@when('I have set the Azure region to "{region}"')
def step_when_set_azure_region(context, region):
    """
    Sets the Azure region in the context properties.

    Args:
        context: Behave context object.
        region: The Azure region to set.
    """
    if not hasattr(context, 'properties'):
        context.properties = SimpleNamespace()
    context.properties.region_name = region
    logging.debug(f"Set Azure region to '{region}'")


@when('I save the following stack tags')
def step_when_save_stack_tags(context):
    """
    Saves one or more stack tags as specified in the context.table.

    Args:
        context: Behave context object containing deployment parameters and template information.
    """
    if context.table:
        tags = []
        for row in context.table:
            tag_name = row['tag']
            tag_value_str = row['value']

            # Parameters may well use interpolated values; try evaluating them.
            try:
                tag_value = get_property(context, tag_value_str)
            except Exception as e:
                logging.debug(f"Expression evaluation failed for '{tag_value_str}': {e}")
                tag_value = tag_value_str

            # Attempt to parse JSON strings into Python objects
            if isinstance(tag_value, str):
                try:
                    tag_value = json.loads(tag_value)
                except json.JSONDecodeError:
                    pass

            tags.append({
                "TagKey": tag_name,
                "TagValue": tag_value
            })

        if tags:
            update_stack_tags(context, tags)

# 'THEN ...' STEPS:


@then('I save the deployment outputs as results')
def step_then_save_deployment_outputs(context):
    """
    Saves the outputs of the deployment as results in the context.

    Args:
        context: Behave context object.
    """
    # Check if we have a stack object with Outputs merged
    if hasattr(context.properties, 'stack') and hasattr(context.properties.stack, 'Outputs'):
        # Retrieve outputs from the local stack definition
        outputs = {o["OutputKey"]: o["OutputValue"] for o in context.properties.stack.Outputs}
    else:
        # Fallback: try retrieving from Azure (if you really need this fallback)
        cloud_provider = context.properties.cloud.lower()
        if cloud_provider == 'azure':
            outputs = context.azure_operator.get_deployment_outputs(context.properties.deployment_name)
        elif cloud_provider == 'aws':
            outputs = context.aws_operator.get_stack_output(context.properties.stack_name)
        else:
            raise Exception(f"Unknown cloud provider: {context.properties.cloud}")

    print(f"Available outputs: {outputs}")

    for row in context.table:
        output_key = row['output']
        result_name = row['result_name']
        output_value = outputs.get(output_key)
        if output_value is None:
            raise AssertionError(f"Output '{output_key}' not found in deployment outputs.")
        print(f"Saved output '{output_key}' as '{result_name}': {output_value}")
        set_test_result(context, result_name, output_value)


@then('I set the test result "{result_name}" to the parameter "{param_name}"')
def step_set_test_result_from_parameter(context, result_name, param_name):
    """
    Sets a previous deployment parameter to context.properties.deployment_parameters.

    Args:
        context: Behave context object containing deployment parameters and template information.
        result_name: Name of desired parameter in context.properties.deployment_parameters
        param_name: Name of parameter in previous deployment
    """
    parameters = getattr(context.properties, 'deployment_parameters', {})
    value = parameters.get(param_name)
    if not value:
        raise ValueError(f"Parameter: '{param_name}' not found in scenario parameters.")
    set_test_result(context, result_name, value)


@then('I verify the stack "{stack_name_expr}" is successfully created')
def step_then_verify_stack_created(context, stack_name_expr):
    """
    Verifies that the specified AWS CloudFormation stack is successfully created.
    """
    stack_name = get_property(context, stack_name_expr)
    logging.debug(f"Verifying stack creation: {stack_name}")

    try:
        stack_status = context.aws_operator.get_stack_status(stack_name)
        if stack_status != 'CREATE_COMPLETE':
            raise AssertionError(f"Stack '{stack_name}' creation failed with status '{stack_status}'.")
        logging.info(f"Stack '{stack_name}' verified successfully.")
    except Exception as e:
        logging.error(f"Error verifying stack creation: {e}")
        raise


@then('I verify the deployment "{deployment_name}" is successful')
def step_then_verify_deployment_successful(context, deployment_name):
    """
    Verifies that the specified deployment is successful.

    Args:
        context: Behave context object.
        deployment_name: The name of the deployment to verify.
    """
    # Evaluate the deployment name expression
    deployment_name = get_property(context, deployment_name)
    logging.debug(f"Verifying deployment: {deployment_name}")

    deployment = context.azure_operator.get_deployment(deployment_name)
    if deployment is None:
        raise AssertionError(f"Deployment '{deployment_name}' does not exist.")

    # Verify the deployment status
    status = deployment.properties.provisioning_state
    if status != 'Succeeded':
        raise AssertionError(f"Deployment '{deployment_name}' failed with status '{status}'.")
    logging.info(f"Deployment '{deployment_name}' succeeded with status '{status}'.")


@then('I verify the deployment "{deployment_name}" no longer exists')
def step_then_verify_deployment_deleted(context, deployment_name):
    """
    Verifies that the specified deployment no longer exists.

    Args:
        context: Behave context object.
        deployment_name: The name of the deployment to verify. Can be a string literal or a 'context.*' variable.
    """
    try:
        deployment_name = get_property(context, deployment_name)
        exists = context.azure_operator.find_deployment(deployment_name)
        if exists:
            raise AssertionError(f"Deployment '{deployment_name}' still exists.")
    except Exception as e:
        logging.error(f"Error verifying deployment deletion: {e}")
        raise


@then('I verify the resource group "{rg_name}" no longer exists')
def step_then_verify_resource_group_deleted(context, rg_name):
    """
    Verifies that the specified resource group no longer exists.

    Args:
        context: Behave context object.
        rg_name: The name of the resource group to verify. Can be a string literal or a 'context.*' variable.
    """
    try:
        rg_name = get_property(context, rg_name)
        exists = context.azure_operator.find_resource_group(rg_name)
        if exists:
            raise AssertionError(f"Resource group '{rg_name}' still exists.")
    except Exception as e:
        logging.error(f"Error verifying resource group deletion: {e}")
        raise


@then('I verify the stack "{stack_name_expr}" no longer exists')
def step_then_verify_stack_deleted(context, stack_name_expr):
    """
    Verifies that the specified AWS CloudFormation stack no longer exists.
    """
    stack_name = get_property(context, stack_name_expr)
    logging.debug(f"Verifying stack deletion: {stack_name}")

    try:
        exists = context.aws_operator.does_stack_exist(stack_name)
        if exists:
            raise AssertionError(f"Stack '{stack_name}' still exists.")
        logging.info(f"Stack '{stack_name}' has been deleted successfully.")
    except Exception as e:
        logging.error(f"Error verifying stack deletion: {e}")
        raise


@then('it should exist')
def step_then_assert_resource_group_exists(context):
    """
    Asserts that the resource group exists.

    Args:
        context: Behave context object.
    """
    if not context.rg_exists:
        raise AssertionError("Resource group does not exist.")


@then('stack should exist')
def step_then_assert_stack_exists(context):
    """
    Asserts that the stack exists.

    Args:
        context: Behave context object.
    """
    if not context.stack_exists:
        raise AssertionError("Stack does not exist.")
