import xml.etree.ElementTree as ET

def truncate_xml_data(xml_file):
    # Parse the XML file
    output_file = 'clean_upload.xml'
    tree = ET.parse(xml_file)
    root = tree.getroot()
    oversize_count = 0
    # Iterate over each <mms> element in the XML
    for mms in root.findall('.//mms'):
        m_size = mms.get('m_size')
        # Check if m_size exists and is greater than 10000
        if m_size and m_size.isdigit() and int(m_size) > 10000:
            # print(f"Found <mms> with m_size={m_size}. Processing <part> elements...")
            oversize_count = oversize_count+1

            # Iterate over each <part> within this <mms>
            for part in mms.findall('.//part'):
                # Check if 'data' attribute exists
                data = part.get('data')
                if data and len(data) > 1000:
                    # Truncate the data attribute to the first 1000 characters
                    truncated_data = data[:10]
                    part.set('data', truncated_data)
                    # print(f"Truncated <part> data to 1000 characters for mms with m_size={m_size}")

    # Write the modified XML to a new file
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"Found {oversize_count} excessive messages.\nModified XML saved to {output_file}")

# Example usage
# input_file = 'GMessages.xml'
# output_file = 'output.xml'
# truncate_xml_data(input_file, output_file)
