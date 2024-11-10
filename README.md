Flask App for Processing SMS and MMS History

This Flask app is designed to process and analyze SMS and MMS data from a personal messaging history. The data is exported from the app SMS Backup & Restore, which generates an XML file containing all SMS and MMS records.

Workflow
XML Upload & Initial Validation: The app accepts XML files, validates the file type and content, and begins processing.
Data Processing:
First Pass: Filters out oversized messages (such as videos) to streamline data.
Second Pass: Parses each message, adding it to a database with fields for id, date, readable_date, address, contact_name, message_content, type, and is_group.
Data Querying: Once processed, the app allows querying of messages based on different criteria.
Key Features
Upload XML Files: Supports XML uploads with built-in validation.
Basic Statistics: View insights like total messages, messages sent/received, and frequent contacts.
Random Message Retrieval: Retrieve a random message from the dataset for casual review.
Search by Contact: Search messages by contact name.
Keyword Search: Filter messages by keywords for targeted information.
Data Visualization: Generate visualizations of message length over time.

