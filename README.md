# Dashboarder

Dashboarder is a tool for managing the monitoring of websites. It rotates through websites you designate at a specified time interval. The tools come preconfigured with webcams showing various national parks and is written in python.


# Files

**config.db**:	contains urls and timeouts in a sqlite db
**websites.json**: config file for the older version Dashboarder4
**requirements.txt**: run a pip install -r requirement.txt to install the necessary libraries.
**DashboarderFancy.py**: The two screen version windowed app that has a preview for the next URL and the zoomed in version of the current URL.

# Setup and Execution

Pull down the code from git or download a zip file. Create a virtual environment with this command: **python -m vent .venv**. Once the virtual environment is created, run **pip install -r requirements.txt** this will install the necessary libraries. Then you can start the tool using the debugger in VSCode or just by running python Dashboarder4.py or python DashboarderFancy.py.

Additional documentation is located here: https://pybri.blogspot.com/2025/12/announcing-dashboarder.html
