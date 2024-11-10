import xml.etree.ElementTree as ET
import hashlib
import sqlite3
import re
from flask import flash, redirect
import logging 
# from db_utils import get_total_messages, get_total_sent_messages, get_total_received_messages, get_random_message, get_most_frequent_sender, get_top_contacts, get_avg_message_length_by_contact
from db_utils2 import get_engine, save_messages_to_db, save_contacts, get_total_messages, get_total_sent_messages, get_total_received_messages, get_random_message, get_most_frequent_sender, get_top_contacts, get_avg_message_length_by_contact
import cProfile
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

contact_cache = {}

# Constants for message types
SMS_TYPE_RECEIVED = 1
SMS_TYPE_SENT = 2
MMS_TYPE_RECEIVED = 132
MMS_TYPE_SENT = 128
max_size_threshold = 1000000
BATCH_SIZE = 10000

def calculate_file_hash(file):
    hasher = hashlib.sha256()
    buf = file.read()
    hasher.update(buf)
    return hasher.hexdigest()

# Function to check if a file is an XML
def is_xml_file(file):
    # Check file extension
    if not file.filename.endswith('.xml'):
        return False

    # Check the file content type
    if file.content_type != 'application/xml' and file.content_type != 'text/xml':
        return False

    return True

def clean_address(phone_number):
    cleaned_number = re.sub(r'[\s\-\(\)\+]', '', phone_number)
    
    # Remove leading '1' if present
    if cleaned_number.startswith('1'):
        cleaned_number = cleaned_number[1:]
    
    # Format to XXX-XXX-XXXX if valid
    if len(cleaned_number) == 10:
        return f'{cleaned_number[:3]}-{cleaned_number[3:6]}-{cleaned_number[6:]}'
    return cleaned_number

def extract_sms_data(elem):
    """Extract SMS data from an 'sms' element."""
    contact_name = elem.get('contact_name', "(Unknown)")
    address = clean_address(elem.get('address'))
    
    if contact_name == "(Unknown)":
        contact_name = get_contact_name_by_address(address)
        # print(f"Unknown SMS found -> {contact_name} | {address}")

    message = {
        'date': elem.get('date'),
        'readable_date': elem.get('readable_date'),
        'address': address,
        'contact_name': contact_name,
        'message_content': elem.get('body'),
        'type': int(elem.get('type')),
        'is_group': 0
    }


    yield "sms", message


def extract_mms_data(elem):
    """Extract MMS data from an 'mms' element."""
    date = elem.get('date')
    readable_date = elem.get('readable_date')
    address_list = elem.get('address')
    contact_name = elem.get('contact_name', "(Unknown)")
    message_content = extract_message_content(elem)
    mms_type = int(elem.get('m_type'))
    message_type = SMS_TYPE_RECEIVED if mms_type == MMS_TYPE_RECEIVED else SMS_TYPE_SENT
    
    is_group = 1 if "~" in address_list else 0
    
    if contact_name == "(Unknown)" and not is_group:
        contact_name = get_contact_name_by_address(address_list)
        # print(f"Unknown SOLO MMS found -> {contact_name} | {address_list}")
    
    if is_group:
        address_list = extract_sender_address(elem)
        contact_name = get_contact_name_by_address(address_list)
        # print(f"Unknown GROUP MMS found -> {contact_name} | {address_list}")

    message = {
        'date': date,
        'readable_date': readable_date,
        'address': clean_address(address_list),
        'contact_name': contact_name,
        'message_content': message_content,
        'type': message_type,
        'is_group': is_group
    }
   
    yield "mms", message  # Added a comma here

def parse_xml(xml_file):
    """Parse the XML file and yield SMS and MMS messages."""
    message_batch = []
    contact_batch = []

    for event, elem in ET.iterparse(xml_file, events=('end',)):
        
        if elem.tag == 'sms':
            for item_type, message in extract_sms_data(elem):
                message_batch.append(message)
                # if message['contact_name'] != "(Unknown)":
                #     contact_batch.append({
                #         'address': message['address'],
                #         'contact_name': message['contact_name']
                #     })
            elem.clear()

        if elem.tag == 'mms':
            # print("Parsing MMS")
            for item_type, message in extract_mms_data(elem):
                message_batch.append(message)

                # if message['contact_name'] != "(Unknown)":
                #     contact_batch.append({
                #         'address': message['address'],
                #         'contact_name': message['contact_name']
                #     })
            elem.clear()  # Clear the element to save memory after processing

        # Save the batch if it reaches a certain size
        if len(message_batch) >= BATCH_SIZE:  # Adjust the batch size as needed
            print('Saving messages batch to DB')
            save_messages_to_db(message_batch)
            message_batch.clear()
            # save_contacts(contact_batch)
            # contact_batch.clear()

    # Save any remaining messages and contacts
    if message_batch:
        print("Saving final message batch to DB")
        save_messages_to_db(message_batch)
        message_batch.clear()
    # if contact_batch:
    #     print("Saving final contact batch to DB")
    #     save_contacts(contact_batch)
    #     contact_batch.clear()
    
def extract_message_content(elem):
    """Extract message content from the <parts> element."""
    message_content = None
    parts = elem.find('parts')
    if parts is not None:
        for part in parts.findall('part'):
            content_type = part.get('ct')
            if content_type == 'application/smil':
                continue
            elif content_type == 'text/plain':
                message_content = part.get('text')
            elif content_type in ('image/jpeg', 'image/gif', 'video/3gpp', 'video/mp4'):
                message_content = content_type.split('/')[-1]  # Just return the type (e.g., 'jpeg')
            else:
                message_content = f"ERROR UNKNOWN ct: {content_type}"
    return message_content

def extract_sender_address(elem):
    """Extract the sender's address from the <addrs> element."""
    addresses = elem.find('addrs')
    if addresses is not None:
        for addr in addresses.findall('addr'):
            if addr.get('type') == '137':  # Sender's address has type 137
                return addr.get('address')
    print("error extracting sender adress")
    return None  # Return None if not found

def get_contact_name_by_address(address):
    address = clean_address(address)

    if address in contact_cache:
        return contact_cache[address]
    engine = get_engine()  
    Session = sessionmaker(bind=engine)

    with Session() as session:
        result = session.execute(
            text('SELECT contact_name FROM contacts WHERE address = :address'),
            {'address': address}
        ).fetchone()
    
    if result:
        contact_cache[address] = result[0]
        return result[0]
    return "(Unknown)"

def generate_summary():
    total_messages = get_total_messages()
    total_sent = get_total_sent_messages()
    total_received = get_total_received_messages()
    random_message = get_random_message()
    most_frequent_sender, most_frequent_sender_count = get_most_frequent_sender()
    top_contacts = get_top_contacts(5)
    avg_lengths = get_avg_message_length_by_contact(500)

    summary_data = {
        'total_messages': total_messages,
        'total_sent': total_sent,
        'total_received': total_received,
        'random_message': random_message,
        'most_frequent_sender': most_frequent_sender,
        'most_frequent_sender_count': most_frequent_sender_count,
        'top_contacts': top_contacts,
        'avg_lengths': avg_lengths,
    }

    return summary_data  

