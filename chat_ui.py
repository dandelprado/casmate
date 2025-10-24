import html

def getchatbubblehtml(sender, message, source=None, user_name=None):
    """
    Render chat bubble with inline styles (guaranteed to work in Streamlit)
    """
    is_casmate = (sender == "CASmate")
    
    if is_casmate:
        label = "CASmate"
    elif user_name:
        label = user_name
    else:
        label = sender
    
    safe_message = html.escape(str(message)).replace('\n', '<br>')
    
    if is_casmate:
        bubble_style = """
            background: #1e3a5f;
            max-width: 75%;
            padding: 16px 20px;
            margin: 14px 0;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            word-wrap: break-word;
            clear: both;
            float: left;
            color: #E6E9EF;
        """
        label_style = "font-weight: 600; margin-bottom: 8px; font-size: 13px; color: #60a5fa;"
    else:
        bubble_style = """
            background: #2d1b4e;
            max-width: 75%;
            padding: 16px 20px;
            margin: 14px 0;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            word-wrap: break-word;
            clear: both;
            float: right;
            color: #E6E9EF;
            border: 1px solid #6366f1;
        """
        label_style = "font-weight: 600; margin-bottom: 8px; font-size: 13px; color: #c084fc;"
    
    content_style = "font-size: 14px; line-height: 1.65;"
    
    src_html = ''
    if source and str(source).strip():
        safe_source = html.escape(str(source).strip())
        src_html = f'<div style="font-size: 10px; color: #8B92A0; margin-top: 10px; padding-top: 8px; opacity: 0.6; font-style: italic; border-top: 1px solid rgba(139, 146, 160, 0.2);">Source: {safe_source}</div>'
    
    bubble_html = f'<div style="{bubble_style}"><div style="{label_style}">{html.escape(str(label))}</div><div style="{content_style}">{safe_message}</div>{src_html}</div><div style="clear: both;"></div>'
    
    return bubble_html

def getfooterhtml():
    return '<div style="position: fixed; left: 0; right: 0; bottom: 0; text-align: center; color: #8B92A0; font-size: 11px; padding: 12px 20px; background: rgba(12, 23, 38, 0.95); border-top: 1px solid rgba(45, 55, 72, 0.5); z-index: 9999; backdrop-filter: blur(10px);">Developed by Dan del Prado • Northwestern University</div>'

