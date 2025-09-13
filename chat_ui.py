def get_chat_bubble_html(sender, message):
    align = "left" if sender == "CASmate" else "right"
    bgcolor = "#e0f7fa" if sender == "CASmate" else "#c8e6c9"
    color = "#004d40" if sender == "CASmate" else "#1b5e20"
    sender_label = f"<b style='color:{color}'>{sender}:</b>"

    html = f"""
    <div style="
        background-color:{bgcolor};
        color: {color};
        padding:10px 15px;
        border-radius:15px;
        margin:10px 0;
        max-width:80%;
        float:{align};
        clear:both;
        word-wrap:break-word;
        ">
        {sender_label} {message}
    </div>
    """
    return html


def get_footer_html():
    return """
    <hr style="margin-top:3rem;">
    <p style='text-align:center; font-size:12px; color:gray; margin-top:1rem;'>
    Developed by Dan del Prado &nbsp; • &nbsp; Northwestern University of Laoag
    </p>
    """
