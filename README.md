A flask app to process all my texting data
I use an app claled SMS Backup & Restore to get an xml file with all my SMS and MMS history.
This flask app takes the xml file.
On the first pass it just looks for messages that are too big (videos) and trims the data.
The second pass adds every message to a table (id, date, readable_date, address, contact_name, message_content, type, is_group).
From there I can query the data as I want

Features
Upload XML Files: Upload XML files for processing, with validation to check file types and content.
Basic Statistics: View total messages, messages sent/received, and frequent contacts.
Random Message Retrieval: Retrieve a random message from the dataset.
Search by Contact: Search for messages by contact name.
Search by key word: Search messages by any key words 
Data Visualization: View message length by time

