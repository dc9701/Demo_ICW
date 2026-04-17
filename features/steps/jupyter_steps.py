"""
jupyter_steps.py.

Description: This module contains the Jupyter step definitions.
"""
from behave import given, then, when
from common import jupyter_functions
import logging
import re
import ast

from common.framework import failed, set_test_result

# 'GIVEN ...' STEPS:


@given("I am connected to Jupyter on stack {stack}")
def step_given_connected_jupyter_stack(context, stack):
    """
    Connect to the Jupyter server for the specified stack and opens a new kernel.

    Args:
        context: Behave context object.
        stack: context.properties.stack_name, with a corresponding unlimited-automation/resources/stacks/{stack}.json definition file.
                May be a string literal or a 'context.*' variable containing the stack name.
    """
    stack = eval(stack) if 'context.' in stack else stack
    if (context.properties.stack):
        if context.properties.marketplace:
            jupyter_functions.connect_to_kernel_marketplace(context)
        else:
            jupyter_functions.connect_to_kernel(context)
    else:
        failed(f"Could not connect to stack: {stack}")

# 'WHEN ...' STEPS:


@when("I open the {notebook} notebook")
def step_when_open_notebook(context, notebook):
    """
    Open the specified notebook.

    Args:
        context: Behave context object.
        notebook: Notebook name (string literal) or 'context.*' variable containing notebook name.
    """
    notebook = eval(notebook) if 'context.' in notebook else notebook
    jupyter_functions.open_notebook(context, notebook)


@when("I upload the {file} notebook to the Jupyter server")
def step_when_upload_file(context, file):
    """
    Upload the specified file to the Jupyter server.

    Args:
        context: Behave context object.
        file: File name (string literal) or 'context.*' variable containing file name.
    """
    file = ast.literal_eval(file) if 'context.' in file else file
    upload_path = 'sql/' + file.split('/')[-1]
    jupyter_functions.upload_file(context, file, upload_path)


@when("I validate the existence of the {notebook} notebook")
def step_when_validate_notebook_existence(context, notebook):
    """
    Validate the existence of the specified notebook.

    Args:
        context: Behave context object.
        notebook: Notebook name (string literal) or 'context.*' variable containing notebook name.
    """
    notebook = eval(notebook) if 'context.' in notebook else notebook
    if not jupyter_functions.notebook_exists(context, notebook):
        failed(f"Notebook '{notebook}' does not exist.")


@when("I validate the contents of the {notebook} notebook")
def step_when_validate_notebook_contents(context, notebook):
    """
    Validate the contents of the specified notebook.

    Args:
        context: Behave context object.
        notebook: Notebook name (string literal) or 'context.*' variable containing notebook name.
    """
    notebook = eval(notebook) if 'context.' in notebook else notebook
    if not jupyter_functions.notebook_contents_valid(context, notebook):
        failed(f"Notebook '{notebook}' contents are not valid.")


@when("I run")
def step_when_run_code_multiline(context):
    """
    Run multi-line code content in the current notebook.

    Args:
        context: Behave context object.
    """
    code = context.text
    try:
        code = eval(f'f"{code}"')
    except Exception:
        try:
            code = eval(f"f'{code}'")
        except Exception:
            code = code
    jupyter_functions.run_command(context, code)


@when("I run '{code}'")
def step_when_run_code(context, code):
    """
    Run the specified code content in the current notebook.

    Args:
        context: Behave context object.
        code: Code to execute (formatted string).
    """
    try:
        code = eval(f'f"{code}"')
    except Exception:
        try:
            code = eval(f"f'{code}'")
        except Exception:
            code = code

    jupyter_functions.run_command(context, code)


@when("I run the '{cmd_regex}' step")
def step_when_run_step(context, cmd_regex):
    """
    Run the commend in a matching code cell without any parameter replacement.

    Args:
        context: Behave context object.
        cmd_regex: A substring or regex used to find a matching command in the notebook's code cells.
    """
    cmd_regex = eval(cmd_regex) if 'context.' in cmd_regex else cmd_regex

    jupyter_functions.run_matching_command(context, cmd_regex)


@when("I run the '{cmd_regex}' step with")
def step_when_run_step_with(context, cmd_regex):
    """
    Run the matching code cell with the specified parameters using a data table.

    Args:
        context: Behave context object.
        cmd_regex: A substring or regex used to find a matching command in the notebook's code cells.
        NOTE: The data table is accessible via context.table
    """
    logging.info(f"Running {cmd_regex}")
    cmd_regex = eval(cmd_regex) if 'context.' in cmd_regex else cmd_regex
    jupyter_functions.run_matching_command(context, cmd_regex, context.table)

# 'THEN ...' STEPS:


@then("I save the output matching '{regex}' as result {property}")
def step_then_save_ouput_as_result(context, regex, property):
    """
    Save part of the last command's output to a JUnitXML property in the test results.

    Args:
        context: Behave context object.
        regex: Regular epxression or string literal to match or 'context.*' variable containing regex to match.
        property: Name of the JUnitXML property.
    """
    regex = eval(regex) if 'context.' in regex else regex
    value = ''
    match_prop = re.search(regex, context.properties.jupyter_notebook.last_command_output)
    if (match_prop):
        try:
            value = match_prop.group(1)
        except Exception:
            value = match_prop.group(0)
    set_test_result(context, property, value)
    logging.info(f"Set test result {property}='{value}'")


@then("I verify the output contains '{regex}'")
def step_then_verify_ouput_contains(context, regex):
    """
    Verify output of the most recently run code contains {regex}.

    Args:
        context: Behave context object.
        regex: Regular epxression or string literal to match or 'context.*' variable containing regex to match.
    """
    regex = eval(regex) if 'context.' in regex else regex
    if re.search(regex, context.properties.jupyter_notebook.last_command_output):
        logging.info(f"VERIFIED OK: Expression '{regex}' was found in output!")
    else:
        failed(f"VERIFICATION FAILED: Expression '{regex}' was NOT found in output:\n{context.properties.jupyter_notebook.last_command_output}")
