import great_expectations as gx
from great_expectations.core.batch import BatchRequest, RuntimeBatchRequest
import os
# DCC from ruamel import yaml

# Define and print data context.
context = gx.get_context(mode="file", project_root_dir="./resources")
# DCC context = gx.get_context()

# Define Snowflake connection.
acct_name = os.getenv("MY_DB_ACCOUNT")
user_name = os.getenv("MY_DB_USERNAME")
password = os.getenv("MY_DB_PASSWORD")

database = "OR_WORKERS_COMP"
schema = "PUBLIC"
warehouse = "COMPUTE_WH"
role = "ACCOUNTADMIN"

sf_conn_string = (
    f"snowflake://{user_name}:{password}@{acct_name}/{database}/{schema}?warehouse={warehouse}&role={role}"
)

# Add Snowflake Datasource
datasource = context.data_sources.add_or_update_snowflake(
    name="snowflake_datasource",
    connection_string=sf_conn_string,
)

# DCC print("[DCC_DEBUG_01] CONTEXT W/ DATASOURCE:\n", context)

# Add CLAIMS table asset and define Batch Request
table_asset = datasource.add_table_asset(
    name="claims_asset",
    table_name="CLAIMS"
)
batch_request = table_asset.build_batch_request()

# Test the connection by retrieving a validator
validator = context.get_validator(
    batch_request=batch_request
)
print(validator.head())

