def inject_css():
    return """
    <style>
      .chat-row {
        display: flex;
        margin: 8px 0;
        width: 100%;
      }
      .left { justify-content: flex-start; }
      .right { justify-content: flex-end; }
      .bubble {
        max-width: 80%;
        padding: 10px 14px;
        border-radius: 14px;
        word-wrap: break-word;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      }
      .casmate {
        background: #e0f7fa;
        color: #004d40;
      }
      .student {
        background: #c8e6c9;
        color: #1b5e20;
      }
      .sender {
        font-weight: 700;
        margin-right: 6px;
      }
    </style>
    """

def get_chat_bubble_html(sender, message, display_label=None):
    is_casmate = (sender == "CASmate")
    row_side = "left" if is_casmate else "right"
    role_class = "casmate" if is_casmate else "student"
    label = display_label if display_label else sender

    return f"""
    <div class="chat-row {row_side}">
      <div class="bubble {role_class}">
        <span class="sender">{label}:</span> {message}
      </div>
    </div>
    """

def get_footer_html():
    return """
    <hr style="margin-top:2rem;">
    <p style="text-align:center; font-size:12px; color:gray;">
      Developed by Dan del Prado • Northwestern University
    </p>
    """

