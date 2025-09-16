def get_chat_bubble_html(sender, message, display_label=None, source=None):
    is_casmate = (sender == "CASmate")
    role_class = "casmate" if is_casmate else "student"
    label = display_label if display_label else sender
    src_html = f'<div class="source">Source: {source}</div>' if (source and str(source).strip()) else ""
    return f'''
      <div class="chat-wrap">
        <div class="bubble {role_class}">
          <div class="label">{label}</div>
          <div class="content">{message}</div>
          {src_html}
        </div>
      </div>
    '''

def get_footer_html():
    return '<div class="footer" style="margin-top:28px;color:#A7B0C0;font-size:12px;text-align:center;">Developed by Dan del Prado • Northwestern University</div>'
