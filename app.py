from flask import Flask, render_template, request, flash, redirect, url_for
from time import time
import os
import pickle
import base64
import email.message
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages

logo_url = 'https://drive.google.com/uc?id=1XJ1MOK5AH5QrZGJd8HtYBYtSNnp7kk8h'
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
TOKEN_PATH = '../../token.pickle'
CREDENTIALS_PATH = r"C:\Users\User\AppData\Roaming\gspread\fcredentials.json"
CC_RECIPIENTS = [
    'liezl@diamed-ph.com',
    'joshua@diamed-ph.com',
    'field_applications2@diamed-ph.com'
]
TO_EMAIL = 'lorenzo@diamed-ph.com'


def authenticate_google_api():
    """Authenticate and return the Google API service."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        creds = refresh_or_get_new_creds(creds)

    save_credentials(creds)
    return build('gmail', 'v1', credentials=creds)


def refresh_or_get_new_creds(creds):
    """Refresh credentials or get new ones if expired or invalid."""
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
    return creds


def save_credentials(creds):
    """Save the credentials to the token file."""
    with open(TOKEN_PATH, 'wb') as token_file:
        pickle.dump(creds, token_file)


def format_subject(subject_details):
    """Format the email subject with appropriate punctuation."""
    if len(subject_details) > 2:
        return f'Anitia Canine IgE I & II: {", ".join(subject_details[:-1])}, and {subject_details[-1]}'
    return f'Anitia Canine IgE I & II: {" and ".join(subject_details)}'


def create_message(to, subject, body, cc=None):
    """Create and return the email message with provided details."""
    msg = email.message.EmailMessage()
    msg.set_content(body, subtype='plain')
    msg.add_alternative(body, subtype='html')
    msg['To'] = to
    msg['Subject'] = subject

    if cc:
        msg['Cc'] = ', '.join(cc)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {'raw': raw_message}


def create_draft(service, message_body):
    """Create a draft email on Gmail."""
    try:
        draft = service.users().drafts().create(userId='me', body={'message': message_body}).execute()
        print(f'Draft created with ID: {draft["id"]}')
        return draft
    except Exception as e:
        print(f"Error creating draft: {e}")
        return None


def build_email_body(sample_details):
    """Generate the email body with the sample details."""
    body = "<p>Hello Doc Soy,</p>"
    body += "<p>Please see the attached Anitia Canine IgE I & II test results for:</p>"
    body += f"<p>{'<br>'.join(sample_details)}</p>"

    # Adding the Thank You part
    body += """
        <p>Thank you very much.</p>
        <p>--</p>
    """
    return body


def build_signature():
    """Generate the email signature."""

    return f"""
        <p><b>Best Regards,</b></p>
        <p><b>Erik T. Azcoitia</b>
        <small style='font-size: 10px;'> | Field Applications Specialist</small><br>
        <small style='font-size: 10px;'>Phone: +639625486642 (Laguna)<br>
        Telefax: +63285844762 (Manila) | +63495360625 (Laguna)<br>
        enquiries@diamed-ph.com (sales) | customer-support@diamed-ph.com (tech support)<br>
        <b>www.diamed-ph.com</b></p>
        <img src='{logo_url}' alt='Company Logo' style='max-width: 200px; height: auto;' /><br>
        <small style='font-size: 10px;'>\"The best way to predict the future is to invent it.\"
    """


def process_samples(num_samples):
    """Process the sample details from the form."""
    sample_details = []
    subject_details = []

    for i in range(1, num_samples + 1):
        place = request.form.get(f'place_{i}', '').strip()
        pet_name = request.form.get(f'pet_name_{i}', '').strip()
        breed = request.form.get(f'breed_{i}', '').strip()
        owner_surname = request.form.get(f'owner_surname_{i}', '').strip()

        if not place or not pet_name or not breed or not owner_surname:
            flash(f"Sample {i} information is incomplete!", "error")
            return redirect(url_for('index'))

        sample_details.append(f'{place}: {pet_name} {owner_surname} ({breed})')
        subject_details.append(f'{place} "{pet_name}"')

    return sample_details, subject_details


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            num_samples = int(request.form['num_samples'])

            # Process form data for samples
            sample_details, subject_details = process_samples(num_samples)

            # Get selected CC recipients from checkboxes
            selected_cc = request.form.getlist('cc')

            # Get new CC recipient from the text box (if provided)
            new_cc = request.form.get('cc_new', '').strip()
            if new_cc:
                selected_cc.append(new_cc)

            # Authenticate Google API
            service = authenticate_google_api()

            # Format email subject and body
            subject = format_subject(subject_details)
            body = build_email_body(sample_details)
            body += build_signature()

            # Create email message with the selected CC recipients
            message_body = create_message(
                to=TO_EMAIL,
                subject=subject,
                body=body,
                cc=selected_cc if selected_cc else CC_RECIPIENTS  # Default to predefined CC if none selected
            )

            # Create draft in Gmail
            create_draft(service, message_body)

            flash('Draft email created successfully!', 'success')
            return redirect(url_for('index'))

        except KeyError as e:
            flash(f"Missing form field: {e}", "error")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('index'))

    return render_template('index.html', timestamp=int(time()))


if __name__ == '__main__':
    app.run(debug=True)
