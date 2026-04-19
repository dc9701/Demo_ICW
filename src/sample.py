import great_expectations as gx
import os
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector

# Define Snowflake connection.
acct_name = os.getenv("MY_DB_ACCOUNT")
user_name = os.getenv("MY_DB_USERNAME")
password = os.getenv("MY_DB_PASSWORD")

database = "OR_WORKERS_COMP"
schema = "PUBLIC"
warehouse = "COMPUTE_WH"
role = "ACCOUNTADMIN"

# Define Snowflake connection.
sf_conn_params = {
    "user": user_name,
    "password": password,
    "account": acct_name,
    "warehouse": warehouse,
    "database": database,
    "schema": schema
}
conn = snowflake.connector.connect(**sf_conn_params)

# Load original table into Snowflake
import_file = "resources/data/OR_WORK_COMP__5000_Clean_Import.csv"
df1 = pd.read_csv(import_file)
success, nchunks, nrows, _ = write_pandas(conn, df1, "CLAIMS", auto_create_table=True, overwrite=True)
print(f"\nImported {nrows} rows from {import_file}...\n")

# Define Great Expectations (GX) data context.
context = gx.get_context(mode="file", project_root_dir="./resources")

# Add Snowflake Datasource for GX.
gx_conn_string = f"snowflake://{user_name}:{password}@{acct_name}/{database}/{schema}?warehouse={warehouse}&role={role}"
datasource = context.data_sources.add_or_update_snowflake(
    name="snowflake_datasource",
    connection_string=gx_conn_string,
)
# Add CLAIMS table asset and define Batch Request.
table_asset = datasource.add_table_asset(
    name="claims_asset",
    table_name="CLAIMS"
)
batch_request = table_asset.build_batch_request()

# Query the CLAIMS table and validate EMPLOYER_NAME equals 'Redacted' about 14.25+% of the time.
validator = context.get_validator(
    batch_request=batch_request
)
result_01 = validator.expect_column_values_to_be_in_set(
    column="Employer_Name",
    value_set=["Redacted"],
    mostly=.2675
)

print(f"\n[DCC_DEBUG] - RESULT_01 - EXPECT EMPLOYER_NAME equals 'Redacted' about 15% of the time (TRUE): {'TRUE' if result_01.success else 'FALSE'}\n")

# Load test CSV into Snowflake.
import_file = "resources/data/OR_WORK_COMP__250_Non_Redacted.csv"
df = pd.read_csv(import_file)
success, nchunks, nrows, _ = write_pandas(conn, df, "CLAIMS", overwrite=False)
conn.close()
print(f"\nImported {nrows} rows from {import_file}...\n")

result_02 = validator.expect_column_values_to_be_in_set(
    column="Employer_Name",
    value_set=["Redacted"],
    mostly=.2675
)

print(f"\n[DCC_DEBUG] - RESULT_02 - EXPECT EMPLOYER_NAME equals 'Redacted' about 15% of the time (FALSE): {'TRUE' if result_02.success else 'FALSE'}\n")
