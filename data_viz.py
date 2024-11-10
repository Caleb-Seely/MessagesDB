import sqlite3
import pandas as pd
import bokeh
from bokeh.plotting import figure, show
from bokeh.models import HoverTool, ColumnDataSource
from bokeh.resources import CDN
from db_utils2 import fetch_messages_for_visualization
js_resources = CDN.js_files
css_resources = CDN.css_files

def create_message_length_plot(messages_df):
    """
    Creates a scatter plot of message lengths over time using Bokeh.
    """
    # Ensure the 'date' column is in datetime format
    # messages_df['date'] = pd.to_datetime(messages_df['date'], errors='coerce')
    messages_df = messages_df.dropna(subset=['date'])

    # Map message types to colors (e.g., 1 for received messages, 2 for sent)
    messages_df['color'] = messages_df['type'].map({1: '#D20103', 2: '#8DB7F5'})
    
    # Prepare data for Bokeh plot
    source = ColumnDataSource(data=dict(
        date=messages_df['date'],
        message_length=messages_df['message_length'],
        message_content=messages_df['message_content'],
        message_contact=messages_df['contact_name'],
        readable_date=messages_df['readable_date'],
        message_type=messages_df['type'],
        color=messages_df['color']

    ))

    # Create the scatter plot figure
    plot = figure(title="Message Length Over Time",
                  tools="box_zoom,reset,pan,box_select",
                  x_axis_label="Date",
                  y_axis_label="Message Length",
                  x_axis_type="datetime",  # Ensures the x-axis is treated as datetime
                  width=1000,
                  height=400)

    # Add scatter plot points
    plot.scatter(x='date', y='message_length', size=8, source=source, color='color', alpha=0.5)

    # Add hover tool to display message content and date
    hover = HoverTool()
    hover.tooltips = [
        ("Date", "@readable_date"),  # Show date in yyyy-mm-dd format
        ("Contact", "@message_contact"),
        ("Message", "@message_content")  # Show only the first 50 chars of message
    ]
    # hover.formatters = {
    #     '@date': 'datetime',  # Format date properly in hover
    # }

    plot.add_tools(hover)
    return plot
