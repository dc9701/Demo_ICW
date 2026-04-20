"""
stack_steps.py.

Description: This module contains the step definitions for the stack.feature file.
"""
# Behave and other imports.
from behave import given, step, then, when
from datetime import datetime
import json
import logging
import os
from types import SimpleNamespace

# Snowflake- and GX-related imports.
import great_expectations as gx
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector

# Our framework-related imports.
from common.framework import generate_unique_id, get_property, get_stack_parameters, get_stack_templates, set_test_result, update_stack_tags
from common.framework import download_marketplace_template, save_stack_def_file

# 'GIVEN ...' STEPS - Initial setup:

@given("I am connected to {db} database")
def step_given_connected_to_database(context, db):
    """
    Connects to the specified database.

    Args:
        context: Behave context object.
        db:      Database name (OR_WORKERS_COMP),
    """
    print(f"STEP: I am connected to {db} database")


# GENERIC STEPS - Perform test actions; may be referenced using "And", "When", "Then" or "Given":

@step("I append data to the {table} table from {import_file}")
def step_when_append_table_from(context, table, import_file):
    """
    Append rows from the import file to the specified table.

    Args:
        context:     Behave context object.
        table:       Table name (CLAIMS).
        import_file: Import filenam without path (e.g., OR_WORK_COMP__250_Non_Redacted.csv)
                        assumes path: 'resources/data/'.
    """
    if '/' not in import_file:
        import_file = f"resources/data/{import_file}"
    print(f"STEP: I append data to the {table} table from {import_file}")


@step("I replace the {table} table with data from {import_file}")
def step_when_replace_table_with_data_from(context, table, import_file):
    """
    Replace the contents of the entire table from the import file.

    Args:
        context:     Behave context object.
        table:       Table name (CLAIMS).
        import_file: Import filenam without path (e.g., OR_WORK_COMP__5000_Clean_Import.csv)
                        assumes path: 'resources/data/'.
    """
    if '/' not in import_file:
        import_file = f"resources/data/{import_file}"
    
    print(f"STEP: I replace the {table} table with data from {import_file}")


@step("I verify {import_file} has a {column} column that is {value} for at least {percent}% of the rows")
def step_then_verify_import_file_has_column_value_for_percent_of_rows(context, import_file, column, value, percent):
    """
    Validate at least ##.##% of the rows match the specified value.

    Args:
        context:     Behave context object.
        import_file: Import filenam without path (e.g., OR_WORK_COMP__5000_Clean_Import.csv)
                        assumes path: 'resources/data/'.
        column:      Column name, case-sensitive (Employer_Name).
        value:       Value to match in column.   
        percent:     Percent as a decimal ##.##, converted to 0.####.
    """
    if '/' not in import_file:
        import_file = f"resources/data/{import_file}"
    percent = float(percent) / 100

    print(f"STEP: I verify {import_file} has a {column} column that is {value} for at least {percent}% of the rows")


# 'THEN ...' STEPS - Verify actual values match expected values:

@then("I verify the {column} column is {value} for at least {percent}% of the rows")
def step_then_verify_column_value_for_percent_of_rows(context, column, value, percent):
    """
    Validate at least ##.##% of the rows match the specified value.

    Args:
        context:  Behave context object.
        column:   Column name, case-sensitive (Employer_Name).
        value:    Value to match in column.   
        percent:  Percent as a decimal ##.##, converted to 0.####.
    """
    percent = float(percent) / 100
    print(f"STEP: I verify the {column} column is {value} for at least {percent}% of the rows")
