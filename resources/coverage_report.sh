#!/bin/bash

pytest --cov=. --cov-branch --cov-report html --cov-config=.coveragerc -c ./pytest.ini
pytest --cov=. --cov-branch --cov-report xml --cov-config=.coveragerc -c ./pytest.ini
