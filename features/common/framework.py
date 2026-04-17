"""
framework.py.

Description:
    This module provides the common functions and classes required for the compute engine test scripts.

Classes:
    - None

Functions (alphabetical):
    - check_internet: Check if there is an internet connection available.
    - collect_run_details: Collect run details in italy.td.teradata.com database via SG2U API.
    - download_template_files: Download a specific file from the GitHub based on the provided parameters.
    - failed: Current test failed, so log an error and throw an AssertionError to be caught by behave.
    - generate_unique_id: Generate a unique ID with the given prefix and length.
    - get_parameters_from_jsonfile: Get the stack parameters from a file (deprecated).
"""
import allure
from datetime import datetime
import logging
import json
import os
import re
import requests
import secrets
import string
import urllib3
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants Section
BASE_URL = 'https://raw.githubusercontent.com/Teradata/ai-unlimited'
AWS_PATH_URL = '{}/{}/deployments/{}/templates/{}/{}-{}.yaml'
AWS_FILE_FORMAT = 'aws_{}-{}.yaml'
AZURE_PATH_URL = '{}/{}/deployments/{}/templates/arm/{}/{}-{}.json'
AZURE_FILE_FORMAT = 'azure_{}-{}.json'
AZURE_INIT_PATH_URL = '{}/{}/deployments/{}/templates/arm/init/resources.json'
AZURE_INIT_FILE_FORMAT = 'azure_resources.json'
AZURE_TEMPLATE_URL = '{}/{}/deployments/{}/templates/arm/{}'
TEMPLATE_FILE_FORMAT = 'UAT_{}_{}-{}.yaml'
DOWNLOAD_PATH = '../downloads'
SUCCESS_MSG = 'Successfully downloaded file {} from {}'
FAILURE_MSG = 'Failed to download file {} from {}. Check if the url is correct and file exist'

# key_map is used to translate AWS property names to Azure property names, which sometimes vary in case.
key_map = {
    # TODO: REG-1506 - Consider adding this 'convience feature' at a later date.
    # 'name': ['name', 'AiUnlimitedName', 'JupyterName', 'Network', 'ResourceGroupName', 'Subnet']
    'AiUnlimitedServerBaseUrl': ['AiUnlimitedServerBaseUrl', 'aiUnlimitedServerBaseUrl']
}


# @deprecated("Do we still need this?")
def check_internet() -> bool:
    """
    Check if there is an internet connection available.

    Args:
        bool: True if there is an internet connection available, False otherwise.
    """
    url = 'http://www.google.com/'
    timeout = 5
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        print("No internet connection available, please try to reconnect.")
    return False


def debug_screenshot(context, element, action='_'):
    """
    Save current screenshot to a file named {timestamp}_{element.id}.png, if current feature file has @debug tag.

    Args:
        context: Behave context object.
        element: A SimpleNamespace with `type` and `id` attributes for locating the element.
    """
    debug = [x for x in context.feature.tags if 'debug' in x]
    if debug:
        filename = '../screenshots/' + datetime.now().strftime('%Y%m%d%H%M%S%f')
        if (element and element.id):
            filename += action + element.id.replace(' ', '_') + '.png'
        context.driver.get_screenshot_as_file(filename)
        logging.info(f"Saved screenshot: {filename}")


def download_template_files(platform: str = 'docker', template_type: str = 'all-in-one', lb_type: str = 'nlb',
                            branch: str = 'develop') -> str:
    """
    Download a specific file from the GitHub repository based on the provided parameters.

    Args:
        branch (str): The branch of the GitHub repository from which to download the file. Default is 'develop'.
        platform (str): The platform for which the file is relevant. Default is 'docker'.
        template_type (str): The type of the template to be downloaded. Default is 'all-in-one'.
        lb_type (str): The type of load balancer used. Default is 'nlb' (network load balancer).

    Returns:
        str: The name of the downloaded file, which includes the current timestamp and the template type and
        load balancer type.
    """
    load_balancer = {
        'wlb': 'without-lb',
        'nlb': 'with-nlb',
        'alb': 'with-alb'
    }

    if platform == 'aws':
        url = AWS_PATH_URL.format(BASE_URL, branch, platform, template_type, template_type, load_balancer[lb_type])
        file_name = AWS_FILE_FORMAT.format(template_type, load_balancer[lb_type])
        downloaded_file_name = '{}/{}'.format(DOWNLOAD_PATH, file_name)
    elif platform == 'azure':
        url = AZURE_TEMPLATE_URL.format(BASE_URL, branch, platform, template_type)
        downloaded_file_name = '{}/{}'.format(DOWNLOAD_PATH, template_type.split('/')[-1])
    else:
        ValueError('Invalid platform. Please provide a valid platform (aws or azure)')

    # Ensure the directory exists
    os.makedirs(os.path.dirname(downloaded_file_name), exist_ok=True)

    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        with open(downloaded_file_name, 'wb') as file:
            file.write(response.content)
        print(SUCCESS_MSG.format(downloaded_file_name, url))
    else:
        print(FAILURE_MSG.format(downloaded_file_name, url))

    return downloaded_file_name


def download_marketplace_template(platform: str = 'azure', template_type: str = 'marketplace', github_token: str = None) -> str:
    """
    Download a specific file from a private GitHub repository using the GitHub API.

    For Azure marketplace templates, this function fetches the file content, decodes it,
    and saves it locally.

    Args:
        platform (str): 'azure'
        template_type (str): 'marketplace'
        github_token (str, optional): Your GitHub personal access token.

    Returns:
        str: The path to the downloaded file.
    """
    # Use the GitHub API endpoint to get file content
    url = "https://api.github.com/repos/Teradata-TIO/compute-engine-marketplace/contents/azure/marketplace.json?ref=develop"
    downloaded_file_name = os.path.join(DOWNLOAD_PATH, "marketplace.json")
    os.makedirs(os.path.dirname(downloaded_file_name), exist_ok=True)

    headers = {}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
        headers['User-Agent'] = "arturo-carballo_teradata"
        logging.info("GitHub token provided for authentication.")
    else:
        logging.info("No GitHub token provided; attempting anonymous access.")

    logging.info(f"Attempting to download marketplace template from URL: {url}")
    try:
        response = requests.get(url, timeout=120, headers=headers)
        logging.info(f"Received response with status code: {response.status_code}")
        logging.debug(f"Response headers: {response.headers}")
        logging.debug(f"Response content (first 200 chars): {response.text}")
    except Exception as e:
        logging.error(f"Exception occurred while trying to download the template: {e}")
        raise

    if response.status_code == 200:
        data = response.json()
        if 'content' in data:
            file_content = base64.b64decode(data['content'])
            with open(downloaded_file_name, 'wb') as file:
                file.write(file_content)
            logging.info(SUCCESS_MSG.format(downloaded_file_name, url))
        else:
            logging.error("Content not found in the API response.")
            raise Exception("Content not found in the API response.")
    else:
        logging.error(FAILURE_MSG.format(downloaded_file_name, url))
        raise Exception(f"Failed to download template. Status code: {response.status_code}")

    return downloaded_file_name


def failed(err_msg: str = "Unexpected error", log_msg: str = ""):
    """
    Fail the current test step and log the error.

    Args:
        err_msg (str): Concise error message to report to behave.
        log_msg (str): Optional verbose error message for logging.
    """
    logging.error(log_msg if log_msg else err_msg)
    raise AssertionError(err_msg)


# @deprecated("Do we still need this?")
def generate_unique_id(prefix: str = "ai-unlimited-", string_lenght: int = 24) -> str:
    """
    Generate a unique ID with the given prefix and length.

    Args:
        prefix (str): The prefix to use for the unique ID.

    Returns:
        str: The generated unique ID.
    """
    if prefix is None:
        prefix = ''

    uuid_length = string_lenght - len(prefix)
    random_string = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(uuid_length))

    unique_id = prefix + random_string

    return unique_id


# @deprecated("Use context.properties.stack, automatically set in environment.py, before_all()")
def get_parameters_from_jsonfile(parameter_file: str) -> list:
    """
    Get the stack parameters from a file.

    Args:
        parameter_file (str): Path to the parameter file

    Returns:
        list: List of stack parameters
    """
    with open(parameter_file, "r") as jsonfile:
        parameters = json.load(jsonfile)

    return parameters


def get_property(context, property_name):
    """
    Get the value of a dot-notated property.

    Args:
        context: Behave context object.
        property_name (str): Name of property as a dot-notation string or an actual property (pass-thru).

            For example, some string references (> 3 nesting levels):
                'context.properties.stack.Parameters.AiUnlimitedVersion'
                'context.properties.stack.Tags.EngineVersion'
            A dot-notation string <= 3 levels:
                'context.properties.region_name'
            Or the actual properties themselves (not necessarily str):
                context.properties.stack.StackId

            Supports expression evaluation, such as:

                'http://{context.properties.stack.Parameters.AiUnlimitedServerBaseUrl}:3282'

    Returns:
        str: String value of parameter if found or the value of an actual property; otherwise, None.

        Cells in a Jupyter notebook - Returns a list of all code cells in the notebook,
        or the source content of the first matching cell:

        Return list of all code cells:
            get_property(context, 'context.properties.jupyter_notebook.content.cells')

            Returns:
                [
                    ["%connect <projectname>"],
                    ["%project_auth_create name=, project=, key=, secret=, region=us-west-2"],
                    ["%project_create project=, env="],
                    . . .
                ]

        Return source of cell matching 'project_auth_create':
            get_property(context, 'context.properties.jupyter_notebook.content.cells.project_auth_create')

            Returns: '%project_auth_create name=, project=, key=, secret=, region=us-west-2'
    """
    property_expr = ''
    property_value = None

    if (not isinstance(property_name, str)):  # An actual property; pass-thru the value.
        return property_name
    elif ('context.' in property_name and property_name.count('.') > 3):  # A dot-notated property > 3 nesting levels.
        key_name = None
        # Handle expressions
        if (isinstance(property_name, str) and "{" in property_name and "}" in property_name):
            match_expr = re.search(r'(.*){(.*)}(.*)', property_name)
            property_expr = 'f"' + match_expr.group(1) + '{property_value}' + match_expr.group(3) + '"'
            property_name = match_expr.group(2)

        # Stack Tags
        match_tags = re.search(r'(.*)\.Tags.(.*)', property_name)
        if (match_tags):
            key_name = 'TagKey'
            value_name = 'TagValue'
            property_key = match_tags.group(2)
            property_list = eval(match_tags.group(1) + '.Tags')
        else:
            # Stack Outputs
            match_outputs = re.search(r'(.*)\.Outputs.(.*)', property_name)
            if (match_outputs):
                key_name = 'OutputKey'
                value_name = 'OutputValue'
                property_key = match_outputs.group(2)
                property_list = eval(match_outputs.group(1) + '.Outputs')
            else:
                # Stack Parameters
                match_params = re.search(r'(.*)\.Parameters.(.*)', property_name)
                if (match_params):
                    key_name = 'ParameterKey'
                    value_name = 'ParameterValue'
                    property_key = match_params.group(2)
                    property_list = eval(match_params.group(1) + '.Parameters')
                else:
                    # Cells in a Jupyter notebook
                    match_cells = re.search(r'(.*)\.jupyter_notebook.content.cells(.*)', property_name)
                    if (match_cells):
                        property_list = eval(match_cells.group(1) + '.jupyter_notebook.content')['cells']
                        property_key = match_cells.group(2)[1:] if (match_cells.group(2).find('.') == 0) else match_cells.group(2)
                        if (property_key):
                            property_key = re.sub(r'\s+', ' ', property_key).replace(r'\n', '').replace(") )", "))")  # Normalize strings.
                            for p in property_list:
                                if ('cell_type' in p and p['cell_type'] == 'code' and 'source' in p):
                                    source = re.sub(r'\s+', ' ', p['source']).replace(r'\n', '').replace(") )", "))")
                                    match_prop = re.search(property_key, source)
                                    if (match_prop or property_key in source):
                                        property_value = p['source']
                        else:
                            property_value = [x['source'] for x in property_list if x['cell_type'] == 'code' and x['source']]

        # Search through Tags, Outputs or Properties items for a matching property_key.
        if (key_name):
            prop_map = key_map[property_key] if property_key in key_map else property_key
            prop_map = [prop_map] if isinstance(prop_map, str) else prop_map
            for prop in prop_map:
                matches = [x[value_name] for x in property_list if x[key_name] == prop]
                if matches and not property_value:
                    property_value = matches[0]

        if (property_expr):
            property_value = eval(property_expr)

    else:  # Everything else.
        try:
            property_value = eval(property_name)
        except Exception as e:
            logging.debug(f"Failed to evaluate property '{property_name}': {e}")
            property_value = property_name

        if (isinstance(property_value, str) and ("{'" in property_value or "'}" in property_value)):
            property_value = str(property_value).replace("{'", "").replace("'}", "")

    return property_value


def get_stack_parameters(context, template={}) -> list:
    """
    Get the stack parameters from current context.table.

    Will map AWS parameter names => Azure parameter names, if necessary.
    Also checks template content to use only valid parameters.

    Args:
        context: Behave context object.

    Returns:
        list: List of stack parameters (excluding 'template(s)')
    """
    if context.table:
        template_type = ''
        if (isinstance(template, str) and 'aws' in template.lower()):  # AWS S3 URL
            template_type = 'aws_url'
        elif (isinstance(template, dict)):
            if ('AWSTemplateFormatVersion' in template):  # AWS template body
                template_type = 'aws'
            elif ('$schema' in template):  # Azure template body
                template_type = 'azure'
        parameters = [] if 'aws' in template_type else {}

        for row in context.table:
            param_name = row['parameter']
            param_value_str = row['value']
            # Parameters may well use interpolated values; try evaluating them.
            try:
                param_value = get_property(context, param_value_str)
            except Exception as e:
                logging.debug(f"Expression evaluation failed for '{param_value_str}': {e}")
                param_value = param_value_str

            # Attempt to parse JSON strings into Python objects
            if isinstance(param_value, str):
                try:
                    param_value = json.loads(param_value)
                except json.JSONDecodeError:
                    pass

            # The 'template(s)' parameter is skipped, being handled by get_stack_templates().
            if ('template' not in param_name.lower()):
                param_list = key_map[param_name] if param_name in key_map else param_name
                param_list = [param_list] if isinstance(param_list, str) else param_list
                for param in param_list:
                    param_key = ''
                    if (template_type == 'aws'):
                        # Add parameter if it exists in the AWS template.
                        param_key = param if ('Parameters' in template and param in template['Parameters']) else ''
                    elif (template_type == 'aws_url'):
                        # Add parameter if it exists in the AWS template.
                        param_key = param if (param.lower() not in ['name']) else ''
                    elif (template_type == 'azure'):
                        # Add parameter if it exists in the Azure template.
                        param_key = param if ('parameters' in template and param in template['parameters']) else ''
                    else:
                        # Add all parameters if no template.
                        param_key = param

                    # If we passed a stack_name, it should be used rather than the env_var AIU_STACK_NAME.
                    if (param.lower() == 'name' and param_value):
                        context.properties.stack_name = param_value

                    # Add parameter if it mapped to a valid param_key in the template (or no template).
                    if param_key:
                        if ('aws' in template_type):
                            parameters.append({
                                'ParameterKey': param_name,
                                'ParameterValue': param_value.__str__()
                            })
                        else:
                            parameters[param_key] = param_value
                        logging.debug(f"Set {template_type} parameter {param_key}={param_value} (type = {type(param_value).__name__})")
    else:
        logging.warning("GET_STACK_PARAMETERS: No stack parameters provided.")

    return parameters


def get_stack_templates(context) -> list:
    """
    Get the list of stack template files from the 'template(s)' parameter in context.table.

    Args:
        context: Behave context object.

    Returns:
        list: List of stack parameters (excluding 'template(s)')
    """
    templates = []
    if context.table:
        for row in context.table:
            param_name = row['parameter']
            param_value = row['value']
            # Template value(s) should be a single string or comma-separated values (not interpolated).
            if ('template' in param_name.lower()):
                if ',' in param_value:
                    templates = param_value.split(',')
                elif ' ' in param_value:
                    templates = param_value.split(' ')
                else:
                    templates.append(param_value)
                logging.debug(f"Parameter '{param_name}': '{param_value}'")
    else:
        logging.warning("GET_STACK_TEMPLATES: No stack parameters provided.")

    return templates


def merge_dicts(dict1={}, dict2={}) -> dict:
    """
    Merges two dicts recursively (deep merge), without overwriting any existing values (keeps values from dict1).

    Args:
        dict1, dict2:  Pretty self-explanatory...

    Returns:
        merged_dict: Resultant dict.
    """
    merged_dict = dict1
    for key, value in dict2.items():
        if key in merged_dict and isinstance(merged_dict[key], dict) and isinstance(value, dict):  # Nested dicts
            merged_dict[key] = merge_dicts(merged_dict[key], value)
        elif key in merged_dict and isinstance(merged_dict[key], list) and isinstance(value, list):  # A list to parse
            # If list in dict1 is NOT Parameters, Outputs or Tags, we don't inspect it's contents.
            if key in ['Parameters', 'Outputs', 'Tags']:
                key_name = {'Parameters': 'ParameterKey', 'Outputs': 'OutputKey', 'Tags': 'TagKey'}[key]
                value_name = {'Parameters': 'ParameterValue', 'Outputs': 'OutputValue', 'Tags': 'TagValue'}[key]
                for item in value:
                    add_item = True
                    for merged_item in merged_dict[key]:
                        if merged_item[key_name] == item[key_name]:  # Don't append a duplicate item to a list.
                            add_item = False
                            break
                    if add_item:
                        merged_dict[key].append({key_name: item[key_name], value_name: item[value_name]})
        else:
            if key not in merged_dict:
                merged_dict[key] = value

    return merged_dict


def save_stack_def_file(context):
    """
    Writes updated stack definition file and pushes to GitHub, then clears stack_updated flag.

    Args:
        context: Behave context object.
    """
    stack_path = os.path.abspath(f"../resources/stacks/{context.properties.stack_name}.json")
    logging.info(f"AFTER_ALL: Saving updates to stack definition file ../resources/stacks/{context.properties.stack_name}.json")
    with open(stack_path, 'w') as stack_def_file:
        stack = context.properties.stack.__dict__
        if ('CreationTime' in stack and hasattr(stack['CreationTime'], 'strftime')):
            stack['CreationTime'] = stack['CreationTime'].strftime("%Y-%m-%d %H:%M:%S")
        stack_def_file.write(json.dumps(stack, indent=4))

    # Push the updated stack file(s) to GitHub (current checkout-out branch).
    git = os.getenv('GIT_PATH', '/usr/bin/git')
    os.system(f"""
        {git} add ../resources/stacks/*
        {git} commit -m 'Updating stack definition file(s)'
        {git} push -f
    """)
    context.properties.stack_updated = False


def save_test_results(context):
    """
    Writes updated reports/allure results and pushes to GitHub.

    Args:
        context: Behave context object.

    # Replace tags with actual values in all results JSON files.
    """
    # Slightly different syntax and no need for 'allure generate' when running via GitHub actions.
    if (os.getenv('GITHUB_ACTIONS')):
        os.system(f"""
        sed -i "s/{{context.properties.test_results.engine_bom_version}}/{context.properties.test_results.engine_bom_version}/g" reports/allure/*.json
        sed -i "s/{{context.properties.stack_name}}/{context.properties.stack_name}/g" reports/allure/*.json >/dev/null 2>&1
        """)
    else:
        os.system(f"""
        sed -i ".bak" "s/{{context.properties.test_results.engine_bom_version}}/{context.properties.test_results.engine_bom_version}/g" reports/allure/*.json
        sed -i ".bak" "s/{{context.properties.stack_name}}/{context.properties.stack_name}/g" reports/allure/*.json >/dev/null 2>&1
        rm reports/allure/*.json*.bak
        """)


def send_request(context, server_url, method='POST', endpoint='', payload='{}'):
    """
    Send an HTTPS request to the jupyter server.

    Args:
        context: Behave context object.
        method: Request method, such as 'POST' (default) or 'GET'.
        endpoint: Optional endpoint added to base Jupyter server URL, such as '/api/kernels'.
        payload: Optional payload, as a JSON-formatted string.

    Returns:
        response: A urllib3.request() response object.
    """
    parsed_url = urllib3.util.parse_url(server_url)
    token = parsed_url.query.split('=')[1] if parsed_url.query else ''
    headers = {'Authorization': f'token {token}', 'content-type': 'application/json'} if token else {'content-type': 'application/json'}

    if hasattr(context.properties, 'jupyter_cookies'):
        headers['Cookie'] = context.properties.jupyter_cookies

        if method == "PUT" or method == "POST":
            xsrf = headers['Cookie'].split(";")[0]
            xsrf = xsrf.split("=")[1]
            headers['x-xsrftoken'] = xsrf

    url = f"{parsed_url.scheme}://{parsed_url.host}{':' + str(parsed_url.port) if parsed_url.port else ''}{endpoint}"
    response = ''

    with urllib3.PoolManager(cert_reqs='CERT_NONE') as conn:
        logging.info(f"Sending {method} request to {url}")
        response = conn.request(method, url, headers=headers, body=payload)
        if (response.status not in [200, 201]):
            failed(f"{method} request failed: {response.status}",
                   f"{method} request failed: {response.status}\n{response.data}")
    return response


def set_test_result(context, property, value):
    """
    Set Allure test report result value (displayed as a link name).

    Args:
        context: Behave context object.
        property (str): Property name, such as 'ENGINE_VERSION'.
        value (str): Property value, such as '20.00.18.29'.

    NOTE: Results may be referenced after being saved; e.g.:  context.properties.test_results.ENGINE_VERSION
    """
    context.properties.test_results.__dict__[property] = value
    allure.dynamic.link(f"https://www.teradata.com/platform/ai-unlimited?{property}={value}", name=f"{property} = {value}")


def update_stack_tags(context, tags={}):
    """
    Add/update one or more stack Tags.

    Args:
        context: Behave context object.
        tags (dict): One or more tags ('key1': 'value1', 'key2': 'value2', ...).  Empty means set default Tags:
            AiUnlimitedWorkspacesURL - If Output.AiUnlimitedUiAccess exists
            AiUnlimitedJupyterURL    - If Output.JupyterUIAccess exists, and add default JupyterToken ('jupyterpass')
    """
    if not tags:
        tags = []
        if get_property(context, 'context.properties.stack.Outputs.AiUnlimitedUiAccess'):
            tags.append({
                "TagKey": "AiUnlimitedWorkspacesURL",
                "TagValue": get_property(context, 'context.properties.stack.Outputs.AiUnlimitedUiAccess').lower()
            })
        if get_property(context, 'context.properties.stack.Outputs.JupyterUIAccess'):
            tags.append({
                "TagKey": "AiUnlimitedJupyterURL",
                "TagValue": get_property(context, 'context.properties.stack.Outputs.JupyterUIAccess') + '/?token=' + context.properties.jupyter_pass
            })
    elif isinstance(tags, dict):
        tags = [tags]

    for tag in tags:
        add_tag = True
        tag_item = 0
        for stack_tag in context.properties.stack.Tags:
            if stack_tag['TagKey'] == tag['TagKey']:  # Found a matching TagKey.
                add_tag = False  # Don't append a duplicate item to a list.
                if stack_tag['TagValue'] != tag['TagValue']:  # Update existing tag with new value.
                    context.properties.stack.Tags[tag_item]['TagValue'] = tag['TagValue']
                    context.properties.stack_updated = True
                break
            tag_item += 1

        if add_tag:
            context.properties.stack.Tags.append({  # Add a new tag.
                "TagKey": tag['TagKey'],
                "TagValue": tag['TagValue']
            })
            context.properties.stack_updated = True


def update_test_status(context):
    """
    Update test status (context.feature.status) via Lake Release Automation API.

    Args:
        context: Behave context object.

    See Also:
        https://lake-release-api.labsteradata.net/docs#/
        https://teradata-pe.atlassian.net/wiki/spaces/CLDI/pages/357796557/Lake+Release+APIs#Get-AIU-BOM
    """
    cloud = context.properties.cloud.upper()
    lra_url = 'https://lake-release-api-dev.labsteradata.net/api/v1/test_status'  # TODO: REGULUS-1650: Remove '-dev' when Rui Y says so.
    request_headers = {"Content-Type": "application/json"}

    result = str(context.feature.status).split('.')[1].lower()
    test_name = context.feature.filename.split('.')[0].split('/')[-1]
    test_suite = [x for x in context.feature.tags if 'subSuite:' in x][0].split(':')[-1] or ''

    data = f"""
    {{
        "pod_id": "",
        "tenant_id": "",
        "test_status": {{
            "test_framework": "ai-u",
            "CIT_AIU_status": {{
                "system_info": {{
                    "site_id": "{context.properties.stack_name}",
                    "cloud_platform": "{cloud}",
                    "engine_bom_version": "{context.properties.test_results.engine_bom_version}"
                }},
                "test_status": {{
                    "{test_suite}": {{
                        "{test_name}": {{
                            "status": "{result}",
                            "report": null,
                            "run_id": "{context.properties.test_results.run_id}"
                        }}
                    }}
                }}
            }}
        }},
        "test_name": "{test_name}",
        "test_team": "ai-u"
    }}
    """

    json_data = json.loads(data)
    response = requests.post(lra_url, headers=request_headers, json=json_data, verify=False)  # noqa: S501 - Call to requests with verify=False
    output = json.loads(response.text)

    if response.status_code == 200:
        logging.info(f"AFTER_FEATURE: Test status for {test_name} updated successfully:\n{response.text}")
        set_test_result(context, 'cloud', cloud)
        set_test_result(context, 'run_id', output['run_id'])
    else:
        logging.error(f"ERROR: {response.text}")


def _normalize_template_ids(templates):
    if isinstance(templates, str):
        return [t.strip() for t in templates.split(',')]
    elif not isinstance(templates, list):
        return [templates]
    return templates
