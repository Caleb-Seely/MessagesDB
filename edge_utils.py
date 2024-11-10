from xml.dom import minidom
import xml.etree.ElementTree as ET
import sqlite3
from file_utils import get_contact_name_by_address, clean_address


def prettify_xml(elem):
    """
    Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def missing_contacts():
    output_file = "missing_contacts.xml"
    conn = sqlite3.connect('messagesDB.db')
    query = f"""
    SELECT readable_date, address, message_content
    FROM messages
    WHERE contact_name IS NULL OR contact_name = "Unknown" or contact_name = ''
    """ 
    
    cursor = conn.cursor()
    cursor.execute(query)
    contacts = cursor.fetchall()

    root = ET.Element("Messages")

    for message in contacts:
        message_elem = ET.Element("Message")


        address = clean_address(message[1])
        # contact_name = get_contact_name_by_address(address)
        # print(f"Conatct: {contact_name} - {address}")

        address_elem = ET.SubElement(message_elem,"address")
        address_elem.text = address

        message_content_elem = ET.SubElement(message_elem, "message_content")
        message_content_elem.text = message[2]

        date_elem = ET.SubElement(message_elem, "date")
        date_elem.text = message[0]

        root.append(message_elem)

    # Prettify the XML and write to file
    xml_str = prettify_xml(root)
    
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write(xml_str)
    print(f"Formatted XML file '{output_file}' created successfully.")

missing_contacts()