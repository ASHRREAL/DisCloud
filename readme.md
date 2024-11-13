Overview
DisCloud is a Python-based cloud storage application that leverages Discord as a platform to store, manage, 
and retrieve files. Using the Discord API, the application uploads files in chunks to a designated Discord 
channel and retrieves them when needed.

Prerequisites
Python 3.7+
Discord Bot with necessary permissions in the target channel
Discord Channel ID and Bot Token
Libraries: Install required libraries using the command:
Copy code
pip install discord aiohttp aiofiles customtkinter pillow

Setup Instructions
Clone the Repository: Download or clone the project files.
Run the Application: Execute python discloud.py.
Configure Discord Settings:
In the "Settings" tab, input your Discord Bot Token and Channel ID.
Click Save Settings and restart the app to apply settings.
Application Structure

Upload Tab:
Select and upload files to the configured Discord channel.
Progress and status updates are displayed.

Manage Files Tab:
View uploaded files with details like name, size, and number of chunks.
Perform actions: Download, Delete, and Refresh file list.

This project is open-source and available for free use and modification.
