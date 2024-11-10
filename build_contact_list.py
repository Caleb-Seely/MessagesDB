import pandas as pd
import sqlite3
from db_utils import print_table_names, print_table_contents, drop_table, create_table
from file_utils import clean_address
import re

# I have a number of messages from "unknown" because I didn't have their contact saved
# I used this to add all my contacts to a table and would refeence it everytime I got a
# message from an unkown sender. It also fixes the edge cases of group messages from 
# contacts I have saved, but never sent individual messages between. 
def add_contacts_from_excel():
    """
    Reads an Excel file, concatenates First Name, Middle Name, Last Name and Phone1-Value, 
    and inserts the result into a 'contacts' table in the database.

    Args:
        excel_file_path (str): Path to the Excel file.
        db_connection (sqlite3.Connection): Connection object to the SQLite database.

    Returns:
        int: The number of contacts added to the database.
    """
    excel_file_path = "My_Contacts.csv"
    db_connection = sqlite3.connect('messagesDB.db')
    # Read the Excel file into a DataFrame
    df = pd.read_csv(excel_file_path)

    # Check if the required columns exist
    required_columns = ['First Name', 'Middle Name', 'Last Name', 'Phone 1 - Value']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Excel file must contain the following columns: {required_columns}")

    # Create a 'Contact Name' column by concatenating First, Middle, and Last Names (handle missing middle names)
    df['Contact Name'] = df['First Name'].fillna('') + ' ' + df['Middle Name'].fillna('')
    df['Contact Name'] = df['Contact Name'].fillna('') + df['Last Name'].fillna('')
    # Clean up any extra spaces in the concatenated name
    df['Contact Name'] = df['Contact Name'].str.strip()

    # Remove any rows without a Phone1-Value
    df = df[df['Phone 1 - Value'].notna()]

    
    # Prepare the SQL query to insert contacts
    query = "INSERT INTO contacts (contact_name, address) VALUES (?, ?)"

    cursor = db_connection.cursor()

    # Insert each row into the contacts table
    for _, row in df.iterrows():

        address = clean_address(row['Phone 1 - Value'])
        cursor.execute("SELECT 1 FROM contacts WHERE address = ?", (address,))
        result = cursor.fetchone()
        if result is None:
            cursor.execute(query, (row['Contact Name'], address))
        else:
            print(f"Dupe| {row['Contact Name']} | {row['Phone 1 - Value']}")

    db_connection.commit()
    cursor.close()

    return len(df)




# Example usage:
# conn = sqlite3.connect('messagesDB.db')


# contacts_added = add_contacts_from_excel()
# print(f'{contacts_added} contacts added to the database.')

# print_table_names()

# drop_table('contacts')
# create_table()
# add_contacts_from_excel()
# print_table_contents('messagesDB.db', 'contacts')