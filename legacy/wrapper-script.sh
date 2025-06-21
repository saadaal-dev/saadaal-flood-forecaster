#!/bin/bash
# This is a simple wrapper to capture the exit code of a cron job
# and send an alert by email in case of failure
#
# Prerequisite is having a mail utility installed, like mailutils:
# sudo apt update; sudo apt install mailutils
#
# Check if a script path was provided as an argument
if [ -z "$1" ]; then
    echo "Error: No script path provided."
    exit 1
fi

script_to_run=$1

if [ ! -f "${script_to_run}" ]; then
    echo "Error: Script ${script_to_run} does not exist."
    exit 1
fi

# Run the script and capture its exit code
if [ -x "${script_to_run}" ]; then
    "${script_to_run}"
else
    bash "${script_to_run}"
fi

# Capture the exit status
status=$?

# Check if the job failed
if [ ${status} -ne 0 ]; then
    # Use the MAILTO environment variable for the email list if mail utility available
    echo "[${script_to_run}] Job failed with exit code ${status}"  # | mail -s "Cron Job Failure Alert" "${MAILTO}"
else
    echo "[${script_to_run}] Job completed successfully."
fi
