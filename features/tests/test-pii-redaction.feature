# REPORTING ANNOTATIONS
@allure.label.parentSuite:nightly_tests
@allure.label.suite:security
@allure.label.subSuite:pii

Feature:  test-pii-redaction - Verify redaction of PII in CLAIMS table meets threshold.
    As a:      Compliance auditor
    I want to: Ensure personally-identifieble information (PII) is redacted upon import
    So I can:  Confirm the databases meet secutiry audit requirements
    .
    # test-pii-redaction.feature
    #
    # Description: Verify redaction of PII in CLAIMS table meets threshold.
    #
    # 1. Setup:
    #   a. Connect to the OR_WORKERS_COMP.PUBLIC Snowflake database.
    #   b. Setup clean test data by replacing CLAIMS table w/ data from OR_WORK_COMP__5000_Clean_Import.csv.
    #
    # 2. Test scenarios:
    #   a. Verify our baseline PII data (Employer_Name) is redacted in AT LEAST 26.75% of the rows.
    #   b. Import 250 non-redacted rows and verify the PII check FAILS (now < 26.75%).
    #
    # 3. Close the Snowflake connection when done.
    #
    # JIRAs:
    #   JIRA-1234 - List the JIRA ticket(s) associated with these tests.

    Scenario: 1. SETUP: Connect to Snowflake and set up clean test data.
        Given I am connected to OR_WORKERS_COMP database
        When I replace the CLAIMS table with data from OR_WORK_COMP__5000_Clean_Import.csv

    Scenario: 2a. Verify our baseline PII data (Employer_Name) is redacted in AT LEAST 26.75% of the rows.
        Then I verify the Employer_Name column is Redacted for at least 26.75% of the rows

    Scenario: 2b. Import 250 non-redacted rows and verify the PII check FAILS (now < 26.75%).
        When I append data to the CLAIMS table from OR_WORK_COMP__250_Non_Redacted.csv
        Then I verify the Employer_Name column is Redacted for at least 26.75% of the rows

    Scenario: 3. Close the Snowflake connection when done.
        Then I close the database connection
