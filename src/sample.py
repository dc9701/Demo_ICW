import great_expectations as gx
import os

# Define and print data context.
context = gx.get_context(mode="file", project_root_dir="./resources")

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
# DCC print("[DCC_DEBUG_01] VALIDATOR:\n", validator.head())

result_01 = validator.expect_column_values_to_be_in_set(
    column="EMPLOYER_NAME",
    value_set=["Redacted"],
    mostly=.1425
).success

print(f"[DCC_DEBUG_01] EXPECT EMPLOYER_NAME equals 'Redacted' about 15% of the time: {'TRUE' if result_01 else 'FALSE'}\n")
