#!/bin/bash

# Just run Uvicorn directly with hardcoded settings
echo -e "\033[0;32mStarting Django with Uvicorn at http://127.0.0.1:8000/\033[0m"
uvicorn web.asgi:application --host=127.0.0.1 --port=8000 --reload
