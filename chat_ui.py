import html
import re


def getchatbubblehtml(sender, message, source=None, user_name=None):
    is_casmate = (sender == "CASmate")
    if is_casmate:
        label = "CASmate"
    elif user_name:
        label = user_name
    else:
        label = sender
    safe_message = html.escape(str(message))
    url_pattern = r'(https?://[^\s]+)'
    safe_message = re.sub(
        url_pattern,
        r'<a href="\1" target="_blank" style="color: #60a5fa; text-decoration: underline;">\1</a>',
        safe_message
    )
    safe_message = safe_message.replace('\n', '<br>')
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
        src_html = f'<div style="margin-top:10px; font-size:12px; opacity:0.7;">Source: {safe_source}</div>'
    return f"""
    <div style="{bubble_style}">
      <div style="{label_style}">{label}</div>
      <div style="{content_style}">{safe_message}</div>
      {src_html}
    </div>
    <div style="clear: both;"></div>
    """


def getfooterhtml():
    return """
    <div style="text-align: center; padding: 20px; margin-top: 30px; border-top: 1px solid #4b5563; color: #9ca3af; font-size: 13px;">
        CASmate &copy; 2025 | Northwestern University CAS
    </div>
    """

