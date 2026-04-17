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

print("[DCC_DEBUG_02] W/ DATASOURCE:\n", context)
