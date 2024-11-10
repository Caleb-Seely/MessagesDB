from flask import Flask
import os
import pandas as pd
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, text, func, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager
from build_contacts_list2 import add_contacts_from_excel

app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()

# Set up the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DATABASE_URL = os.getenv('DATABASE_URL')
# print("Database URL:", os.getenv('DATABASE_URL'))  
# Initialize SQLAlchemy
db = SQLAlchemy(app)
Base = declarative_base()
engine = None  # Global variable to hold the engine
metadata = None

# Create an engine connected to your database
def get_engine():
    global engine
    if engine is None:
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800
        )
    return engine

@contextmanager
def get_session():
    engine = get_engine()  # Create the engine
    Session = sessionmaker(bind=engine)  # Define the session factory
    session = Session()  # Create a new session
    try:
        yield session  # Yield the session to the caller
    finally:
        session.close()  # Ensure the session is closed after use

# Create a MetaData instance
def get_metadata(engine):
    global metadata
    if metadata is None:
        metadata = MetaData()
        metadata.reflect(bind=engine)
    return metadata

# Define the Messages model (you can include other models here as needed)
class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String)  # Change to Date if you prefer
    readable_date = Column(String)
    address = Column(String)
    contact_name = Column(String)
    message_content = Column(Text)
    type = Column(Integer)
    is_group = Column(Integer)

    def __repr__(self):
        return f"<Message id={self.id} contact_name={self.contact_name} date={self.date} message_content{self.message_content}>"

# Define the Contact model
class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, unique=True, nullable=False)
    contact_name = Column(String, nullable=False)

    def __repr__(self):
        return f"<Contact(id={self.id}, address='{self.address}', contact_name='{self.contact_name}')>"

def create_table(table_class):
    print(f"Creating table: {table_class.__tablename__}")
    engine = get_engine()
    table_class.__table__.create(bind=engine, checkfirst=True)

def clean_db():
    delete_table("messages")
    # delete_table("contacts")
    create_table(Message)
    # create_table(Contact)

def print_column_names(table_name):
    engine = get_engine()
    metadata = get_metadata(engine)

    if table_name in metadata.tables:
        table = metadata.tables[table_name]
        column_names = [column.name for column in table.columns]
        print(f"Column names in '{table_name}': {column_names}")
    else:
        print(f"Table '{table_name}' does not exist.")

# Delete a table
def delete_table(table_name):
    engine = get_engine()
    metadata = get_metadata(engine)

    if table_name in metadata.tables:
        Table(table_name, metadata, autoload_with=engine).drop(engine)
        print(f"Table '{table_name}' has been deleted.")
    else:
        print(f"Table '{table_name}' does not exist.")  

def create_contacts_table():
    metadata = MetaData()
    contacts_table = Table(
        'contacts', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('address', String, unique=True, nullable=False),
        Column('contact_name', String, nullable=False)
    )
    engine = get_engine()
    metadata.create_all(engine)  # Creates the table if it doesn't exist

def save_messages_to_db(messages):
    with get_session() as session:
        session.bulk_insert_mappings(Message, messages)  # Replace Message with your ORM model
        session.commit()

def save_contacts_bulk(contacts):
    with get_session() as session:
        session.bulk_insert_mappings(Contact, contacts)  # Replace Message with your ORM model
        session.commit()

def save_contacts(contacts):
    query = text('''
        INSERT INTO contacts (address, contact_name)
        VALUES (:address, :contact_name)
        ON CONFLICT (address) DO NOTHING
    ''')
    with get_session() as session:
        session.execute(query, contacts)
        session.commit()


def print_table_contents(table_name):
    with get_session() as session:
        metadata = get_metadata(engine)
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
            results = session.query(table).all()
            column_names = [column.name for column in table.columns]
            print(column_names)
            for row in results:
                print([getattr(row, column) for column in column_names])
        else:
            print(f"Table '{table_name}' does not exist.")

def print_all_table_names():
    engine = get_engine()  # Assuming you have a function to get your SQLAlchemy engine
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    for table_name in table_names:
        print(table_name)

def get_total_messages():
    with get_session() as session:  # Using context manager
        total_messages = session.execute(text('SELECT COUNT(*) FROM messages')).scalar()
        return total_messages 

def get_random_message():
    with get_session() as session:
        message = session.execute(text('SELECT * FROM messages ORDER BY RANDOM() LIMIT 1')).fetchone()

        if message is None:
            return "No messages found in the database."
        
        return dict(message._mapping)

def get_total_sent_messages():
    with get_session() as session:
        return session.execute(text('SELECT COUNT(*) FROM messages WHERE type = 2')).scalar()
    
def get_total_received_messages():
    with get_session() as session:
        return session.execute(text('SELECT COUNT(*) FROM messages WHERE type = 1')).scalar()

def get_messages_sent(contact_name):
    with get_session() as session:
        result = session.execute(text('SELECT COUNT(*) FROM messages WHERE contact_name = :contact_name AND type = 2'), 
                                 {'contact_name': contact_name})
        count = result.scalar()  # Fetch the scalar result (the count)
        return count
    
def get_messages_received(contact_name):
    with get_session() as session:
        result = session.execute(text('SELECT COUNT(*) FROM messages WHERE contact_name = :contact_name AND type = 1'), 
                                 {'contact_name': contact_name})
        count = result.scalar()  # Fetch the scalar result (the count)
        return count

def get_messages_total(contact_name):
    with get_session() as session:
        result = session.execute(text('SELECT COUNT(*) FROM messages WHERE contact_name = :contact_name'), 
                                 {'contact_name': contact_name})
        count = result.scalar()  # Fetch the scalar result (the count)
        return count
    
#Returns all the messages of a contact 
def get_all_messages(contact_name):
    with get_session() as session:
        result = session.execute(
            text('''
                SELECT readable_date, message_content, type 
                FROM messages 
                WHERE contact_name = :contact_name 
                ORDER BY date DESC
            '''),
            {'contact_name': contact_name}
        ).fetchall()
        
        return result
    
def get_recent_message(contact_name):
    with get_session() as session:
        message = session.execute(text('SELECT * FROM messages WHERE contact_name = :contact_name ORDER BY date DESC LIMIT 1'),
                                  {'contact_name': contact_name}).fetchone()
        return message

def get_top_contacts(limit):
    with get_session() as session:
        contacts = session.execute(text(f'SELECT contact_name, COUNT(*) as message_count FROM messages GROUP BY contact_name ORDER BY message_count DESC LIMIT {limit}')).fetchall()
        
        # Convert each Row to a tuple or dictionary
        return [(contact.contact_name, contact.message_count) for contact in contacts]  # List of tuples

def get_most_frequent_sender():
    with get_session() as session:
        sender = session.execute(text('''
        SELECT contact_name, COUNT(*) as message_count
        FROM messages
        GROUP BY contact_name
        ORDER BY message_count DESC
        LIMIT 1
    ''')).fetchone()
      
        if sender is None:
            print("Error, no sender found")
            return "No most frequent sender found", 0
    
        return sender[0], sender[1]
    
def contact_exists(contact_name):
    with get_session() as session:
        contact = session.execute(text('SELECT COUNT(*) FROM messages WHERE contact_name = :contact_name'),
                                  {'contact_name':contact_name}).scalar()
        return contact > 0

def get_avg_message_length_by_contact(min_messages):
    with get_session() as session:
        results = session.execute(
            text(f'''
                SELECT contact_name, AVG(LENGTH(message_content)) as avg_length, COUNT(*) as message_count
                FROM messages
                WHERE message_content IS NOT NULL AND contact_name != '(Unknown)' AND contact_name IS NOT NULL
                GROUP BY contact_name
                HAVING COUNT(*) > :min_messages
                ORDER BY avg_length DESC
            '''),
            {'min_messages': min_messages}
        ).fetchall()
        
        # Convert to list of tuples with proper types
        return [(contact.contact_name, float(contact.avg_length), contact.message_count) for contact in results]

def search_messages_by_keyword(search_term):
    query = text("""
        SELECT contact_name, address, readable_date, message_content, type
        FROM messages 
        WHERE message_content ILIKE :search_term  -- ILIKE for case-insensitive search
        ORDER BY date DESC
    """)

    # Use wildcards (%) for partial matches
    search_term = f'%{search_term}%'

    with get_session() as session:
        result = session.execute(query, {'search_term': search_term})
        return result.fetchall()

def print_table_contents(table_name):
    query = text(f"SELECT * FROM {table_name}")

    with get_session() as session:
        result = session.execute(query)
        rows = result.fetchall()

        if not rows:
            print(f"No records found in the table '{table_name}'.")
            return
        
        # Print column names
        column_names = result.keys()
        print(f"Printing contents of the table '{table_name}':")
        print(" ".join(column_names))  # Print column headers

        # Print each row
        for row in rows:
            print(" ".join(str(value) for value in row))  # Print row values

def fetch_messages_for_visualization(contact_name=None):
    query = '''
    SELECT readable_date, date, SUBSTRING(message_content, 1, 50) AS message_content, LENGTH(message_content) AS message_length, contact_name, type
    FROM messages
    '''
    if contact_name:
        query += ' WHERE contact_name = :contact_name'  # Use named parameter for SQLAlchemy

    try:
        with get_session() as session:
            # Execute the query, with a parameter if contact_name is provided
            result = session.execute(text(query), {'contact_name': contact_name} if contact_name else {})
            
            # Load result into a DataFrame
            messages_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

    return messages_df

def print_all_unknown_msgs(contact_name):
    with get_session() as session:
        result = session.execute(
            text('''
                SELECT readable_date, address, message_content, type 
                FROM messages 
                WHERE contact_name = :contact_name 
                ORDER BY date DESC
            '''),
            {'contact_name': contact_name}
        ).fetchall()      

        # Print each row
        for row in result:
            print(" ".join(str(value) for value in row))  # Print row values

# add_msg()
# print_all_table_names()
# print_table_contents('messages')
# print_column_names('messages')  # Replace 'messages' with your actual table name
# delete_table('user')         # Replace 'messages' with your actual table name
# create_messages_table()          # Call this to create the messages table
# for x in range(2):
# add_msg()

# print(fetch_messages_for_visualization('Test'))
# create_table(Contact)
# test_save_contacts()

# contacts = add_contacts_from_excel()
# delete_table('contacts')
# create_table(Contact)
# save_contacts(add_contacts_from_excel())
# print_table_contents('contacts')
# print(f'{len(contacts)} contacts added to the database.')
# print_all_unknown_msgs("(Unknown)")