"""
jupyter_functions.py.

Description: Functions to interact with Jupyter.

Classes:
    - None

Functions:
    - create_kernel(context, kernel_name, server_url): Create a kernel in the jupyter server.
"""
from datetime import datetime
import json
import logging
import re
import ssl
from types import SimpleNamespace
import urllib3
import uuid
import os
from websocket import create_connection
import requests
import time

from common.framework import failed, get_property, send_request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def login_jupyter(context):
    """
    Perform Jupyter server login to obtain authentication cookies.

    The function performs:
      1. A GET request to the login page to obtain the initial _xsrf cookie and extract the _xsrf form token.
      2. A POST request with the extracted token and password.
    It saves the resulting cookies in context.properties.jupyter_cookies.
    """
    # Retrieve the base Jupyter URL from the context
    if hasattr(context.properties.stack.Tags, 'AiUnlimitedJupyterURL'):
        raw_jupyter_url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    else:
        outputs_map = {o['OutputKey']: o['OutputValue'] for o in context.properties.stack.Outputs}
        if ('PublicJupyterUI' in outputs_map):  # AWS capitalization
            raw_jupyter_url = outputs_map['PublicJupyterUI'] + '?token=' + context.properties.jupyter_pass
        elif ('publicJupyterUI' in outputs_map):  # Azure capitalization
            raw_jupyter_url = outputs_map['publicJupyterUI'] + '?token=' + context.properties.jupyter_pass

        new_url = {
            'TagKey': 'AiUnlimitedJupyterURL',
            'TagValue': raw_jupyter_url
        }
        context.properties.stack.Tags.append(new_url)

    jupyter_url = raw_jupyter_url.split('?')[0]

    # Step 1: GET request to obtain initial _xsrf cookie and login form token
    login_get_url = f"{jupyter_url}/login?next=/lab"
    session = requests.Session()
    get_resp = session.get(login_get_url, verify=False)
    if get_resp.status_code not in [200, 201]:
        failed("Jupyter login GET request failed", f"Status code: {get_resp.status_code}\nResponse: {get_resp.text}")

    # Extract _xsrf from cookies and from the login form in the HTML response.
    xsrf_cookie = session.cookies.get('_xsrf')
    token_match = re.search(r'name="_xsrf" value="([^"]+)"', get_resp.text)
    xsrf_form_value = token_match.group(1) if token_match else xsrf_cookie

    cookie_header = "; ".join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])

    # Step 2: POST request to perform login, sending the extracted _xsrf token and the password.
    login_post_url = f"{jupyter_url}/login?next=%2Flab"
    login_data = {
        "_xsrf": xsrf_form_value,
        "password": context.properties.jupyter_pass
    }
    headers = {
        "Cookie": cookie_header
    }
    post_resp = session.post(login_post_url, data=login_data, headers=headers, verify=False)
    if post_resp.status_code not in [200, 201]:
        failed("Jupyter login POST request failed", f"Status code: {post_resp.status_code}\nResponse: {post_resp.text}")

    # Combine cookies into a single header string in the format required (key=value; key2=value2)
    cookies = session.cookies.get_dict()
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    context.properties.jupyter_cookies = cookie_header
    logging.info(f"Logged in to Jupyter, obtained cookies: {cookie_header}")


def connect_to_kernel_marketplace(context, kernel_name='teradatasql'):
    """
    Connect to a kernel running on the jupyter server.

    Args:
        context: Behave context object.
        kernel_name: Optional kernel name to connect to (default = 'teradatasql').
    """
    if not hasattr(context.properties, 'jupyter_cookies'):
        login_jupyter(context)

    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')

    response = send_request(context, url, 'GET', '/api/kernels')
    if (response.status in [200, 201]):
        kernel_list = json.loads(response.data)

        # Initialize Kernel if kernel_list is empty
        if kernel_list == []:
            create_kernel(context)
            response = send_request(context, url, 'GET', '/api/kernels')
            kernel_list = json.loads(response.data)

        _kernel = [x for x in kernel_list if x['name'] == kernel_name][0]

        context.properties.jupyter_kernel = SimpleNamespace(**_kernel)
        logging.info(f"Connected to Jupyter '{context.properties.jupyter_kernel.name}' " +
                     f"kernel ({context.properties.jupyter_kernel.id})\n{context.properties.jupyter_kernel.__repr__()}")
    else:
        failed(f"Could not connect to Jupyter kernel named '{kernel_name}': {response.status}",
               f"Could not connect to Jupyter kernel named '{kernel_name}': {response.status}\n{response.data}")


def connect_to_kernel(context, kernel_name='teradatasql'):
    """
    Connect to a kernel running on the jupyter server.

    Args:
        context: Behave context object.
        kernel_name: Optional kernel name to connect to (default = 'teradatasql').
    """
    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    response = send_request(context, url, 'GET', '/api/kernels')
    if (response.status in [200, 201]):
        kernel_list = json.loads(response.data)
        _kernel = [x for x in kernel_list if x['name'] == kernel_name][0]
        context.properties.jupyter_kernel = SimpleNamespace(**_kernel)
        logging.info(f"Connected to Jupyter '{context.properties.jupyter_kernel.name}' " +
                     f"kernel ({context.properties.jupyter_kernel.id})\n{context.properties.jupyter_kernel.__repr__()}")
    else:
        failed(f"Could not connect to Jupyter kernel named '{kernel_name}': {response.status}",
               f"Could not connect to Jupyter kernel named '{kernel_name}': {response.status}\n{response.data}")


def create_kernel(context):
    """
    Create a kernel in the jupyter server.

    Args:
        context: Behave context object.
    """
    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    response = send_request(context, url, 'POST', '/api/kernels', json.dumps({"name": "teradatasql"}))
    if (response.status in [200, 201]):
        _kernel = json.loads(response.data)
        context.properties.jupyter_kernel = SimpleNamespace(**_kernel)
        time.sleep(2)  # Give the kernel a couple of seconds to start properly
        logging.info(f"Connected to Jupyter kernel ({context.properties.jupyter_kernel.id})\n{context.properties.jupyter_kernel.__repr__()}")


def open_notebook(context, notebook):
    """
    Open an existing notebook on the jupyter server.

    If found, context.properties.jupyter_notebook is created, containing only the CODE cell contents.

    Args:
        context: Behave context object.
        notebook: Name of existing notebook, used to create actual path:  'GetStarted' => '/GetStarted.ipynb'
    """
    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    response = send_request(context, url, 'GET', f"/api/contents/{notebook}.ipynb")
    if (response.status in [200, 201]):
        _notebook = json.loads(response.data)
        context.properties.jupyter_notebook = SimpleNamespace(**_notebook)
        context.properties.jupyter_notebook.last_command = ''
        context.properties.jupyter_notebook.last_command_output = ''
        context.properties.jupyter_notebook.last_command_status = ''
        cells = get_property(context, 'context.properties.jupyter_notebook.content.cells')
        logging.info(f"Loaded {context.properties.jupyter_notebook.name} notebook, containing {len(cells)} code cells")


def upload_file(context, file_path, upload_path, server_url=None):
    """
    Upload a file to the jupyter server. If the file already exists, it is not uploaded.

    Args:
        context: Behave context object.
        file_path: Path to the file to upload.
        upload_path: Path to upload the file to on the server.
        server_url: Optional server URL to upload the file to.
    """
    if server_url is None:
        server_url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    file_name = os.path.basename(file_path)
    # Checking first if the file to upload already exists
    try:
        response = send_request(context, server_url, 'GET', f"/api/contents/{upload_path}")
        if (response.status in [200, 201]):
            _file = json.loads(response.data)
            context.properties.jupyter_file = SimpleNamespace(**_file)
            logging.info(f"File {context.properties.jupyter_file.name} already exists")
        else:
            failed(f"Could not check if file '{upload_path}' exists: {response.status}\n{response.data}")
    except AssertionError:
        logging.info(f"File {file_name} does not exist, proceeding to upload.")

        with open(file_path, 'r') as file:
            file_content = file.read()
            payload = json.dumps({
                "type": "file",
                "format": "text",  # Change to "base64" if we are loading a binary file
                "content": file_content,
            })
            response = send_request(context, server_url, 'PUT', f"/api/contents/{upload_path}", payload=payload)
            if (response.status in [200, 201]):
                _file = json.loads(response.data)
                context.properties.jupyter_file = SimpleNamespace(**_file)
                logging.info(f"Uploaded file {context.properties.jupyter_file.name}")
            else:
                failed(f"Could not upload file '{upload_path}': {response.status}\n{response.data}")


def notebook_exists(context, notebook):
    """
    Check if a notebook exists on the jupyter server.

    Args:
        context: Behave context object.
        notebook: Name of existing notebook, used to create actual path:  'GetStarted' => '/GetStarted.ipynb'

    Returns:
        True if the notebook exists, False otherwise.
    """
    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    response = send_request(context, url, 'GET', f"/api/contents/{notebook}.ipynb")
    return response.status in [200, 201]


def run_command(context, command=''):
    """
    Run a notebook command via websocked t=connection.

    Args:
        context: Behave context object.
        command: Command to run on Jupyter kernel.

    Returns:
        output: Command output (JSON string); also written to context.properties.jupyter_notebook.last_command_output.
    """
    endpoint = f"/api/kernels/{get_property(context, 'context.properties.jupyter_kernel.id')}/channels"
    server_url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL')
    parsed_url = urllib3.util.parse_url(server_url)
    if parsed_url.query is not None:
        token = parsed_url.query.split('=')[1]
    headers = {'Authorization': f'Token {token}', 'content-type': 'application/json'}
    scheme = 'wss' if parsed_url.scheme.lower() == 'https' else 'ws'

    # Open a websocket connection
    url = f"{scheme}://{parsed_url.host}:{parsed_url.port}{endpoint}?token={token}"
    ssl_opt = {
        "cert_reqs": ssl.CERT_NONE,
        "check_hostname": False,
        "server_hostname": parsed_url.host
    }
    if hasattr(context.properties, 'jupyter_cookies'):
        logging.info(f"Jupyter Cookies detected: {context.properties.jupyter_cookies}")
        headers['Cookie'] = context.properties.jupyter_cookies

    logging.info(f"Url = {url}, header = {headers}, ssl = {ssl_opt}")
    ws = create_connection(url, header=headers, sslopt=ssl_opt)

    # Compose command message content
    content = {'code': command, 'silent': False}
    hdr_send = {'msg_id': uuid.uuid1().hex,
                'username': 'test',
                'session': uuid.uuid1().hex,
                'data': datetime.now().isoformat(),
                'msg_type': 'execute_request',
                'version': '5.0'}
    msg_send = {'header': hdr_send,
                'parent_header': hdr_send,
                'metadata': {},
                'content': content}

    # Clear last completed command/output, and send new command to kernel and wait for the output
    context.properties.jupyter_notebook.last_command = command
    context.properties.jupyter_notebook.last_command_output = ''
    context.properties.jupyter_notebook.last_command_status = 'RUNNING'
    output = ''
    command_complete = False
    command_failed = False
    command_started = False
    command_timeout = False
    start_time = datetime.now()
    wait_for_progress = 3
    wait_for_completion = 1800

    # Wait up to 3 seconds for a stream message indicating progress, then up to 30 mins for command completion
    logging.info(f"Command RUNNING: '{command}'")
    ws.send(json.dumps(msg_send))
    while not (command_complete or command_timeout):
        msg = json.loads(ws.recv())
        # Check messages in the stream for the result of our execution
        if (msg['msg_type'] in ['execute_result', 'stream', 'error']):
            content = msg['content']
            if (msg['msg_type'] == 'stream'):
                output = content['text']
                if (content['name'] in ['stdout', 'stderr']):
                    command_started = True
                    command_failed = command_failed or content['name'] == 'stderr'
            elif (msg['msg_type'] == 'execute_result'):
                if ('text/markdown' in content['data']):
                    output = content['data']['text/markdown']
                elif ('application/vnd.teradata.resultset' in content['data']):
                    output = content['data']['application/vnd.teradata.resultset']
                elif ('application/vnd.vegalite.v3+json' in content['data']):
                    output = content['data']['application/vnd.vegalite.v3+json']
                else:
                    output = content['data']['text/plain']
                command_started = True
            elif (msg['msg_type'] == 'error'):
                output = f"{content['ename']}: {content['evalue']}\n{content['traceback']}"
                command_complete = True
                command_failed = True

            # Display output in real-time and append to context.properties.jupyter_notebook
            if (len(output) > 1000):
                logging.info("Command OUTPUT (>1000 chars):\n" + output[:500] + "\n. . .\n" + output[-500:])
            else:
                logging.info(f"Command OUTPUT:  {output}")
            context.properties.jupyter_notebook.last_command_output += str(output)

        if command_started:
            command_timeout = (datetime.now() - start_time).total_seconds() > wait_for_completion
            command_complete = command_timeout or (msg['msg_type'] == 'status' and 'execution_state' in msg['content'] and
                                                   'idle' in msg['content']['execution_state'])
        else:
            command_timeout = (datetime.now() - start_time).total_seconds() > wait_for_progress

    if (command_failed):
        context.properties.jupyter_notebook.last_command_status = 'TIMEOUT'
        failed("Command FAILED!\n{context.properties.jupyter_notebook.last_command_output}")
    elif (command_timeout):
        context.properties.jupyter_notebook.last_command_status = 'FAILED'
        failed(f"Command TIMEOUT after {int((datetime.now() - start_time).total_seconds())} secs!" +
               f"\n{context.properties.jupyter_notebook.last_command_output}")
    else:
        context.properties.jupyter_notebook.last_command_status = 'PASSED'
        logging.info("Command SUCCESSFUL")

    # Close websocket connection & return output
    ws.close()
    return output


def run_matching_command(context, cmd_regex='', values=''):
    """
    Create a kernel in the jupyter server.

    Args:
        context: Behave context object.
        cmd_regex: Command 'regex' - finds first matching command in notebook.content.cells.
                    TODO: Just matches 'contains the substring'; could make full regex in framework.get_property(), if needed.
        values: Optional table of values used to populate the command.  Supports numerous command syntax variants:

            %connect <projectname>
            %project_auth_create name=, project=, key=, secret=, region=us-west-2
            %workspaces_config host="http://<IP>:3282", apikey="", withtls=true

            1. A field's value will only be updated if the table contains a value.
            2. A blank value in the table will REMOVE the argument from the command line.
            3. If quotes are specified in the command, they will be retained; no need to add quotes around the value in the table.
            4. Any field in context.table not having a corresponding placeholder in the command will added to the end.

    Returns:
        output: Command output (JSON string); also written to context.properties.jupyter_notebook.last_command_output.
    """
    cmd_orig = get_property(context, f"context.properties.jupyter_notebook.content.cells.{cmd_regex}")
    cmd = cmd_orig
    if (cmd_orig):
        if (values):
            for row in values:
                field = row['field']
                value = get_property(context, row['value'])
                match_tags = re.search(f"(.*)({field})(.*)", cmd)
                if (match_tags):
                    # Matches: <field>, {field}, [field] or (field)
                    if (match_tags.group(1)[-1:] in "<{[()]}" and match_tags.group(3)[0:1]):
                        cmd = re.sub(f"(.*)({field})(.*)", f"{match_tags.group(1)[0:-1]}{value}{match_tags.group(3)[1:]}", cmd)
                    else:
                        match_tags = re.search(f'(.*)({field}=)"(.*?)"(.*)', cmd)
                        if (match_tags):
                            # Matches: Field equals optional value in double-quotes:  field="[{value}]"
                            cmd = re.sub(f'(.*)({field}=)"(.*?)"(.*)', f'{match_tags.group(1)}{field}="{value}"{match_tags.group(4)}', cmd)
                        else:
                            match_tags = re.search(f"(.*)({field}=)'(.*?)(.*)", cmd)
                            if (match_tags):
                                # Matches: Field equals optional value in single-quotes:  field='[{value}]'
                                cmd = re.sub(f"(.*)({field}=)'(.*?)'(.*)", f"{match_tags.group(1)}{field}='{value}'{match_tags.group(4)}", cmd)
                            else:
                                match_tags = re.search(f"(.*)({field}=)(.*?),(.*)", cmd)
                                if (match_tags):
                                    # Matches: Field equals optional unquoted value with trailing comma:  field=[{value}],
                                    cmd = re.sub(f"(.*)({field}=)(.*?),(.*)", f"{match_tags.group(1)}{field}={value},{match_tags.group(4)}", cmd)
                                else:
                                    match_tags = re.search(f"(.*)({field}=)(.*?)$", cmd)
                                    if (match_tags):
                                        # Matches: Field equals optional unquoted value at EOL:  field=[{value}]
                                        cmd = re.sub(f"(.*)({field}=)(.*?)$", f"{match_tags.group(1)}{field}={value}", cmd)
                                    else:
                                        cmd += f", {field}={value}"
                # Add a new field=value to the command (two cases, above & below)
                else:
                    cmd += f", {field}={value}"

        return run_command(context, cmd)
    else:
        logging.warning(f"Unable to find command matching '{cmd_regex}'")
