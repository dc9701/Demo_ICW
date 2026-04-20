"""
stack_steps.py.

Description: This module contains the step definitions for the stack.feature file.
"""
# Behave and other imports.
from behave import given, step, then
import logging

# Snowflake-related imports.
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector

# 'GIVEN ...' STEPS - Initial setup:

@given("I am connected to {db} database")
def step_given_connected_to_database(context, db):
    """
    Connects to the specified Snowflake database and creates associated GX datasource if successful.

    Args:
        context: Behave context object.
        db:      Database name (OR_WORKERS_COMP),
    """
    if db:
        context.properties.sf_database = db
        context.properties.sf_conn_params = {
            "user":      context.properties.sf_user_name,
            "password":  context.properties.sf_password,
            "account":   context.properties.sf_acct_name,
            "warehouse": context.properties.sf_warehouse,
            "database":  context.properties.sf_database,
            "schema":    context.properties.sf_schema
        }
    try:
        context.properties.sf_conn = snowflake.connector.connect(**context.properties.sf_conn_params)
        logging.info(f"Successfully connected to {db} database...\n")

        gx_conn_string = f"snowflake://{context.properties.sf_user_name}:{context.properties.sf_password}@{context.properties.sf_acct_name}/{context.properties.sf_database}/{context.properties.sf_schema}?warehouse={context.properties.sf_warehouse}&role={context.properties.sf_role}"
        context.properties.gx_datasource = context.properties.gx_context.data_sources.add_or_update_snowflake(
            name="snowflake_datasource",
            connection_string=gx_conn_string,
        )
    except Exception as e:
        assert False, f"Unable to connect to {db} database due to:\n{e}"


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
        import_file = f"../resources/data/{import_file}"

    dataframe = pd.read_csv(import_file)
    success, nchunks, nrows, _ = write_pandas(context.properties.sf_conn, dataframe, table, overwrite=False)
    logging.info(f"Appended {nrows} rows to {table} from {import_file}...\n")


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
        import_file = f"../resources/data/{import_file}"

    dataframe = pd.read_csv(import_file)
    success, nchunks, nrows, _ = write_pandas(context.properties.sf_conn, dataframe, table, auto_create_table=True, overwrite=True)
    logging.info(f"Replaced {nrows} rows in {table} from {import_file}...\n")


@step("I verify {import_file} has a {column} column that is {value} for at least {percent}% of the rows")
def step_then_verify_import_file_has_column_value_for_percent_of_rows(context, import_file, column, value, percent):
    """
    Validate at least ##.##% of the rows match the specified value in the import file.

    Args:
        context:     Behave context object.
        import_file: Import filenam without path (e.g., OR_WORK_COMP__5000_Clean_Import.csv)
                        assumes path: 'resources/data/'.
        column:      Column name, case-sensitive (Employer_Name).
        value:       Value to match in column.   
        percent:     Percent as a decimal ##.##, converted to 0.####.
    """
    if '/' not in import_file:
        import_file = f"../resources/data/{import_file}"

    # We import the CSV content and validate the dataframe directly, without adding data to Snowflake.
    import_dataframe = pd.read_csv(import_file)
    data_source = context.properties.gx_context.data_sources.add_or_update_pandas(name="pandas_datasource")
    data_asset = data_source.add_dataframe_asset(name="import_data")
    batch_request = data_asset.build_batch_request({"dataframe": import_dataframe})

    validator = context.properties.gx_context.get_validator(
        batch_request=batch_request
    )
    result = validator.expect_column_values_to_be_in_set(
        column=column,
        value_set=[value],
        mostly=float(percent) / 100
    )
    assert result.success == True, f"The {column} column does NOT match '{value}' for at least {percent}% of the rows in {import_file}"


# 'THEN ...' STEPS - Verify actual values match expected values:

@then("I verify the {column} column in the {table} table is {value} for at least {percent}% of the rows")
def step_then_verify_column_value_for_percent_of_rows(context, table, column, value, percent):
    """
    Validate at least ##.##% of the rows match the specified value.

    Args:
        context:  Behave context object.
        column:   Column name, case-sensitive (Employer_Name).
        table:    Table name (CLAIMS).
        value:    Value to match in column.   
        percent:  Percent as a decimal ##.##, converted to 0.####.
    """
    # Add CLAIMS table asset and define Batch Request.
    table_asset = context.properties.gx_datasource.add_table_asset(
        name=table.lower() + "_asset",
        table_name=table
    )
    batch_request = table_asset.build_batch_request()

    # Query the CLAIMS table and validate EMPLOYER_NAME equals 'Redacted' at least {percent}% of the time.
    validator = context.properties.gx_context.get_validator(
        batch_request=batch_request
    )
    result = validator.expect_column_values_to_be_in_set(
        column=column,
        value_set=[value],
        mostly=float(percent) / 100
    )
    assert result.success == True, f"FAILED:  {table}.{column} does NOT match '{value}' for at least {percent}% of the rows"
