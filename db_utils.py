# db_utils.py
from email import message
import sqlite3
import pandas as pd

# Utilitys for when I was using SQLite3
# No longer using once I moved over to postgress 

def get_db_connection():
    return sqlite3.connect('messagesDB.db')

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,       
        date TEXT,
        readable_date TEXT,
        address TEXT,
        contact_name TEXT,        
        message_content TEXT,
        type INTEGER,
        is_Group INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts(
        address TEXT PRIMARY KEY,
        contact_name TEXT
    ) ''')
    
    print(f"New table created")

    conn.commit()
    conn.close()

def clean_db():
    drop_table('messages')
    create_table()
    

def print_col_names():
    with sqlite3.connect('messagesDB.db') as conn:
        cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(messages);")
    columns_info = cursor.fetchall()
    columns = [info[1] for info in columns_info]
    print("Columns in 'messages' table:", columns)

    cursor.execute("PRAGMA table_info(contacts);")
    columns_info = cursor.fetchall()
    columns = [info[1] for info in columns_info]
    print("Columns in 'contacts' table:", columns)

# Drop a table
def drop_table(table_name):
    """   
    Parameters:
    - table_name: Name of the table to drop.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        print(f"Table '{table_name}' dropped successfully.")
    except sqlite3.Error as e:
        print(f"Error occurred: {e}")
    finally:
        cursor.close()

def get_total_messages(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages')
    return cursor.fetchone()[0]

def get_total_sent_messages(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages WHERE type = 2')
    return cursor.fetchone()[0]

def get_total_received_messages(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages WHERE type = 1')
    return cursor.fetchone()[0]

def get_random_message(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages ORDER BY RANDOM() LIMIT 1')
    
    result = cursor.fetchone()
    
    if result is None:
        # Handle the case where there are no messages
        return "No messages found in the database."
    
    return result

def get_most_frequent_sender(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT contact_name, COUNT(*) as message_count
        FROM messages
        GROUP BY contact_name
        ORDER BY message_count DESC
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    
    if result is None:
        # Handle case when no messages are found
        return "No senders found", 0
    
    return result[0], result[1]

# I'm not surewhy this is here, useless i think. data_viz has a similar funtion I use
# def fetch_messages_for_visualization(conn):
#     print("Fetching messages for viz")
#     return pd.read_sql_query("SELECT date, type FROM messages", conn)

# Total messages sent to a contact
def get_messages_sent(contact_name, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages WHERE contact_name = ? AND type = 2', (contact_name,))
    return cursor.fetchone()[0]


# Total messages received from a contact
def get_messages_received(contact_name, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages WHERE contact_name = ? AND type = 1', (contact_name,))
    return cursor.fetchone()[0]

# Total # of messages between a contact
def get_messages_total(contact_name, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()
    cursor.execute(' SELECT COUNT(*) FROM messages WHERE contact_name = ?', (contact_name,))  

    return cursor.fetchone()[0]

def get_recent_message(contact_name, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM messages 
        WHERE contact_name = ? 
        ORDER BY date DESC LIMIT 1
    ''', (contact_name,))
    last_message = cursor.fetchone()

    return last_message

def contact_exists(contact_name, conn=None):
    if conn is None:
        conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE contact_name = ?', (contact_name,)) 
    result = cursor.fetchone()[0]    
    return result > 0

# Print all messages of a contact
def get_all_messages(contact_name, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT readable_date, message_content, type 
        FROM messages 
        WHERE contact_name = ? 
        ORDER BY date DESC
    ''', (contact_name,))
    
    messages = cursor.fetchall()
    conn.close()

    return messages

def get_message_lengths_over_time(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT readable_date, LENGTH(message_content), message_content, contact_name as message_length FROM messages')
    return cursor.fetchall()

def get_top_contacts(limit, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    query = f"""
    SELECT contact_name, COUNT(*) AS message_count
    FROM messages
    WHERE contact_name IS NOT NULL
    GROUP BY contact_name 
    ORDER BY message_count DESC
    LIMIT {limit}
    """ 
    
    cursor = conn.cursor()
    cursor.execute(query)
    top_contacts = cursor.fetchall()
  

    return top_contacts

def get_avg_message_length_by_contact(min_messages=50, conn=None):
    if conn is None:
        conn = sqlite3.connect('messagesDB.db')
    query = f"""
    SELECT contact_name, AVG(LENGTH(message_content)) AS avg_message_length, COUNT(*) AS message_count
    FROM messages
    WHERE message_content IS NOT NULL AND contact_name != '(Unknown)' AND contact_name IS NOT NULL
    GROUP BY contact_name
    HAVING message_count > ?
    ORDER BY avg_message_length DESC
    """
    cur = conn.cursor()
    cur.execute(query, (min_messages,))
    result = cur.fetchall()
    return result  # Returns a list of (contact_name, avg_message_length) tuples

def search_messages_by_keyword(search_term, conn):
    query = """
        SELECT contact_name, address, readable_date, message_content, type
        FROM messages 
        WHERE message_content LIKE ?
        ORDER BY date DESC
    """
    # Use wildcards (%) for partial matches
    search_term = f'%{search_term}%'
    cur = conn.cursor()
    cur.execute(query, (search_term,))
    results = cur.fetchall()
    
    return results

def print_table_names():
    conn = sqlite3.connect('messagesDB.db')
    cursor = conn.cursor()
    
    # Query to get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    
    # Fetch all results
    tables = cursor.fetchall()
    
    # Print table names
    print("Tables in the database:")
    for table in tables:
        print(table[0])
    
    cursor.close()


# Print everything in a table
def print_table_contents(db_path, table_name):
    # db_path = 'messagesDB.db'  # Path to your database
    # table_name = 'contacts'  # Replace with the name of your table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Retrieve all data from the table
    query = f"SELECT * FROM {table_name}"
    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        # Get the column names
        column_names = [description[0] for description in cursor.description]

        # Print the column names
        print(f"Table: {table_name}")
        print(", ".join(column_names))

        # Print each row in the table
        for row in rows:
            print(row)

    except sqlite3.Error as e:
        print(f"Error retrieving data from table {table_name}: {e}")

    finally:
        # Close the connection
        conn.close()

