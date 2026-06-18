from langchain_core.tools import tool

@tool
def send_email(email_address: str) -> str:
    """
    Sends an email to the specified email address.
    Use this tool whenever the user asks you to send an email.
    
    Args:
        email_address: The recipient's email address.
        
    Returns:
        A confirmation message indicating the email was sent.
    """
    # In a real app, this would integrate with SMTP, SendGrid, Resend, etc.
    print(f"DEBUG: Sending email to {email_address} with subject Hello Buddy")
    
    return "Email sent successfully"
