"""MCP-style wrapper for Gmail API.

Enables reading emails, searching, labeling, and parsing for PARA capture.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import settings
import base64
import logging

logger = logging.getLogger(__name__)


class GmailMCP:
    """MCP-style wrapper for Gmail API."""

    def __init__(self, user_credentials: Dict):
        """Initialize Gmail client.

        Args:
            user_credentials: Dict with 'access_token' and 'refresh_token'
        """
        self.credentials = Credentials(
            token=user_credentials['access_token'],
            refresh_token=user_credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def get_unread_emails(self, max_results: int = 100) -> List[Dict]:
        """Get unread emails.

        Args:
            max_results: Maximum number of emails to fetch

        Returns:
            List of email messages with metadata
        """
        try:
            # Get unread message IDs
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                # Get full message details
                email = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                emails.append(self._parse_email(email))

            return emails

        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
            return []

    def search_emails(
        self,
        query: str,
        max_results: int = 50,
        after: Optional[datetime] = None
    ) -> List[Dict]:
        """Search emails with Gmail query syntax.

        Args:
            query: Gmail search query (e.g., "from:alice subject:budget")
            max_results: Maximum number of results
            after: Only emails after this date

        Returns:
            List of matching emails
        """
        try:
            # Build query
            search_query = query
            if after:
                date_str = after.strftime('%Y/%m/%d')
                search_query = f"{query} after:{date_str}"

            # Search
            results = self.service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                email = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                emails.append(self._parse_email(email))

            return emails

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Get a specific email by ID.

        Args:
            email_id: Gmail message ID

        Returns:
            Parsed email or None
        """
        try:
            email = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            return self._parse_email(email)

        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None

    def add_label(self, email_id: str, label_name: str) -> bool:
        """Add a label to an email.

        Args:
            email_id: Gmail message ID
            label_name: Label to add (e.g., "PARA/Processed")

        Returns:
            True if successful
        """
        try:
            # Get or create label
            label_id = self._get_or_create_label(label_name)

            # Add label to email
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'addLabelIds': [label_id]}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error adding label to email {email_id}: {e}")
            return False

    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read.

        Args:
            email_id: Gmail message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> Optional[str]:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            html: Whether body is HTML

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            message = MIMEMultipart('alternative') if html else MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            if html:
                message.attach(MIMEText(body, 'html'))

            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            return sent_message['id']

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return None

    def _parse_email(self, email: Dict) -> Dict:
        """Parse Gmail API email response into clean dict.

        Args:
            email: Raw Gmail API response

        Returns:
            Parsed email with clean fields
        """
        headers = {h['name']: h['value'] for h in email['payload']['headers']}

        # Extract body
        body = ''
        if 'parts' in email['payload']:
            for part in email['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data', '')
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    break
        elif 'body' in email['payload']:
            body_data = email['payload']['body'].get('data', '')
            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

        return {
            'id': email['id'],
            'thread_id': email['threadId'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'snippet': email.get('snippet', ''),
            'label_ids': email.get('labelIds', []),
            'is_unread': 'UNREAD' in email.get('labelIds', []),
            'is_important': 'IMPORTANT' in email.get('labelIds', [])
        }

    def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID, creating it if it doesn't exist.

        Args:
            label_name: Label name (e.g., "PARA/Processed")

        Returns:
            Label ID
        """
        try:
            # List all labels
            labels = self.service.users().labels().list(userId='me').execute()

            # Find matching label
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    return label['id']

            # Label doesn't exist - create it
            label = self.service.users().labels().create(
                userId='me',
                body={
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
            ).execute()

            return label['id']

        except Exception as e:
            logger.error(f"Error getting/creating label: {e}")
            return 'INBOX'  # Fallback

    def get_threads(self, query: str = '', max_results: int = 50) -> List[Dict]:
        """Get email threads (conversations).

        Args:
            query: Gmail search query
            max_results: Maximum threads to return

        Returns:
            List of threads with all messages
        """
        try:
            results = self.service.users().threads().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            threads = []
            for thread_info in results.get('threads', []):
                thread = self.service.users().threads().get(
                    userId='me',
                    id=thread_info['id']
                ).execute()

                parsed_thread = {
                    'id': thread['id'],
                    'snippet': thread.get('snippet', ''),
                    'message_count': len(thread.get('messages', [])),
                    'messages': [self._parse_email(msg) for msg in thread.get('messages', [])]
                }

                threads.append(parsed_thread)

            return threads

        except Exception as e:
            logger.error(f"Error fetching threads: {e}")
            return []
