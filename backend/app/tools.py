from langchain_core.tools import tool


@tool
def send_email(email_address: str, subject: str, body: str) -> str:
    """
    Sends an email to the specified email address.
    Use this tool whenever the user asks you to send an email.

    When asked to send an email:
    1. Ask the user for the recipient email address and subject if not provided.
    2. Generate a complete draft of the email body yourself based on the user's intent.
    3. Call this tool with the generated body. The system will pause to get human approval.
    4. If the user denies and asks for changes, update the body according to their feedback and call this tool again.

    Args:
        email_address: The recipient's email address.
        subject: The subject line of the email.
        body: The complete drafted content of the email body.

    Returns:
        A confirmation message indicating the email was sent.
    """
    # In a real app, this would integrate with SMTP, SendGrid, Resend, etc.
    print(f"DEBUG: Sending email to {email_address}\nSubject: {subject}\nBody: {body}")

    return "Email sent successfully"
