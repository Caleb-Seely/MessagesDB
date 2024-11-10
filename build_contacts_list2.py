import pandas as pd
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
    contact_batch = []
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

    # Insert each row into the contacts table
    for _, row in df.iterrows():

        address = clean_address(row['Phone 1 - Value'])

        contact_batch.append({
            'address': address,
            'contact_name': row['Contact Name']
        })
        # print(f"Added | {row['Contact Name']} | {address}")

    return contact_batch


def clean_address(phone_number):
    cleaned_number = re.sub(r'[\s\-\(\)\+]', '', phone_number)
    
    # Remove leading '1' if present
    if cleaned_number.startswith('1'):
        cleaned_number = cleaned_number[1:]
    
    # Format to XXX-XXX-XXXX if valid
    if len(cleaned_number) == 10:
        return f'{cleaned_number[:3]}-{cleaned_number[3:6]}-{cleaned_number[6:]}'
    return cleaned_number

