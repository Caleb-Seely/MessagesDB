from wsgiref.util import request_uri
from flask import Flask, request,session, render_template, redirect, flash, jsonify, url_for
import os
import pickle
from db_utils2 import search_messages_by_keyword, clean_db, get_all_messages, get_random_message, get_messages_sent, get_messages_received, get_messages_total, get_recent_message, contact_exists
from file_utils import calculate_file_hash, parse_xml, is_xml_file, generate_summary
from data_viz import fetch_messages_for_visualization, create_message_length_plot
from bokeh.embed import components
import cProfile
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from clean_xml import truncate_xml_data
app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load environment variables from .env file
load_dotenv()

# Set up the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print("Database URL:", os.getenv('DATABASE_URL'))  
clean_db()
# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Route for the homepage
@app.route('/')
def index():
    print("Requested URL:", request.url)
    clean_db()
    return render_template('index.html')

@app.route('/uploaded_data')
def uploaded_data():
    if 'summary_data' in session:
        summary_data = session['summary_data']
        # Create the Bokeh scatter plot        
        messages_df = fetch_messages_for_visualization()
        plot = create_message_length_plot(messages_df)
        script, div = components(plot)

        return render_template('result.html', **summary_data, script=script, div=div)
    else:
        flash('No summary data found')
        return redirect('/')

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Processing file upload...")

    file = request.files.get('file')

    if not file or not file.filename or not is_xml_file(file):
        flash('Please upload a valid XML file')
        return redirect("/")

    # # For testing - to avoid processing data everytime 
    # file_hash = calculate_file_hash(file)
    # cache_file = get_cache_path(file_hash)
    # if os.path.exists(cache_file):  # Load cached data if exists
    #     with open(cache_file, 'rb') as f:
    #         data = pickle.load(f)  # Capture cached data
    #     print(f"Loaded cached data for {file.filename}")
    # else:

    print("Processing new upload")
    file.seek(0)
    file_content = file.read()
    if not file_content:
        flash('Uploaded file is empty')
        return redirect("/")
    
    # # Create independent file streams for SMS and MMS processing
    # file_sms = BytesIO(file_content)

    # Moved up to the initial route to save time
    # clean_db()

    # A few media messages were causing havoc on program memory because there were >100000byts
    # this allows me to cleanup those edge cases
    # it runs through the uploaded file, and anytime it finds <mms> with m_sie (>)100000
    # truncate the data to 10 and copy everythin into 'clean_upload.xml'
    file.seek(0)
    truncate_xml_data(file)

    # The start of the heavy lifting
    try:
        parse_xml('clean_upload.xml')
    except Exception as e:
        print(f"Error during parsing: {e}")

    # # Cache the database for testing purposes
    # with open(cache_file, 'wb') as f:
    #     pickle.dump('messagesDB.db', f)
    #     print('Cached database for future use')

    # Generate summary and visualization
    print("Generating summary")
    summary_data = generate_summary()
    session['summary_data'] = summary_data

    if summary_data['total_messages'] == 0:
        flash('No messages found')
        return redirect("/")

    messages_df = fetch_messages_for_visualization()
    plot = create_message_length_plot(messages_df)
    script, div = components(plot)
    os.remove('clean_upload.xml')
    return render_template('result.html', **summary_data, script=script, div=div)

# Generate a random message
@app.route('/random_message', methods=['GET'])
def get_new_random_message():
    print("Get random message")
    random_message = get_random_message()

    return jsonify({
        'id': random_message.get('id'),
        'date': random_message.get('readable_date'),
        'contact_name': random_message.get('contact_name'),
        'message_content': random_message.get('message_content'),
        'type': random_message.get('type')
    })

# Search a contact 
@app.route('/search_by_contact', methods=['GET', 'POST'])
def search_by_contact():
    show_all= False

    if request.method == 'POST':
        contact_name = request.form.get('contact_name')
        show_all = request.form.get('show_all_messages')
    else:
        # If the request is a GET request, we fetch the contact_name from the URL query string
        contact_name = request.args.get('contact_name')
        

    if not contact_name:
        flash('Please enter a contact name')
        return render_template('contact_search_result.html',
                               contact_name=contact_name)

    # Fetch contact information from the database
    if not contact_exists(contact_name):
        flash(f'No messages found for contact: {contact_name}')
        return render_template('contact_search_result.html',
                                contact_name=contact_name)

    # Extract information
    total_sent = get_messages_sent(contact_name)
    total_received = get_messages_received(contact_name)
    total_messages = get_messages_total(contact_name)
    last_message = get_recent_message(contact_name)
    messages_df = fetch_messages_for_visualization(contact_name)
    # Data viz by contact name
    plot = create_message_length_plot(messages_df)
    # Embed the plot into HTML components
    script, div = components(plot)
    
    messages = get_all_messages(contact_name)
    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            'readable_date': message[0],
            'message_content': message[1],
            'type': message[2]
        })

    
    return render_template('contact_search_result.html',
                           contact_name=contact_name,
                           total_sent=total_sent,
                           total_received=total_received,
                           total_messages=total_messages,
                           last_message=last_message,
                           formatted_messages=formatted_messages,
                           show_all=show_all,
                           script=script,
                           div=div)

@app.route('/search_by_word', methods=['POST'])
def search_by_word():
    search_term = request.form.get('search_term')

    if not search_term:
        flash('Please enter a keyword or phrase to search for.')
        return redirect(url_for('result'))
    
    # Fetch messages containing the search term
    matching_messages = search_messages_by_keyword(search_term)

    formatted_messages = []
    for message in matching_messages:    
        formatted_messages.append({
            'contact_name': message[0],
            'address': message[1],
            'readable_date': message[2],
            'message_content':message[3],
            'type': message[4]
        })
    total_matches = len(formatted_messages)
    return render_template('keyword_search_results.html', search_term=search_term, messages=formatted_messages, total_matches=total_matches)


@app.route('/bokeh_plot')
def bokeh_plot():
    "Bokeh plot"
    # Fetch messages data for visualization
    messages_df = fetch_messages_for_visualization()

    # Create the Bokeh scatter plot
    plot = create_message_length_plot(messages_df)
    # Embed the plot into HTML components
    script, div = components(plot)

    # Render template for the Bokeh plot
    return render_template('bokeh_plot.html', script=script, div=div)

# Helper functions for file validation
def is_xml_file(file):
    return file.filename.endswith('.xml') and file.content_type in ['application/xml', 'text/xml']

def get_cache_path(file_hash):
    return f'uploads/{file_hash}.pkl'

if __name__ == '__main__':
    app.run(debug=True)
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)