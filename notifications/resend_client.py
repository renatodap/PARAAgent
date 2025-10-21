import resend
from config import settings
from typing import Dict, Any

resend.api_key = settings.RESEND_API_KEY

class EmailService:
    """Email notification service using Resend"""

    def __init__(self):
        self.from_email = settings.EMAIL_FROM
        self.from_name = "PARA Autopilot"

    async def send_weekly_review(
        self,
        to_email: str,
        user_name: str,
        review_data: Dict[str, Any]
    ) -> bool:
        """Send weekly review email"""

        html = self._weekly_review_template(user_name, review_data)

        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": f"Your Weekly Review is Ready - {review_data.get('week_start_date', '')}",
                "html": html,
            }

            email = resend.Emails.send(params)
            return True

        except Exception as e:
            print(f"Failed to send weekly review email: {str(e)}")
            return False

    async def send_task_reminder(
        self,
        to_email: str,
        user_name: str,
        tasks: list[Dict[str, Any]]
    ) -> bool:
        """Send task reminder email"""

        html = self._task_reminder_template(user_name, tasks)

        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": f"You have {len(tasks)} tasks due soon",
                "html": html,
            }

            email = resend.Emails.send(params)
            return True

        except Exception as e:
            print(f"Failed to send task reminder: {str(e)}")
            return False

    async def send_approval_pending(
        self,
        to_email: str,
        user_name: str,
        approval_type: str,
        message: str
    ) -> bool:
        """Send pending approval notification"""

        html = self._approval_template(user_name, approval_type, message)

        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": f"Approval Needed: {approval_type}",
                "html": html,
            }

            email = resend.Emails.send(params)
            return True

        except Exception as e:
            print(f"Failed to send approval email: {str(e)}")
            return False

    def _weekly_review_template(self, user_name: str, review_data: Dict[str, Any]) -> str:
        """HTML template for weekly review"""

        wins = review_data.get('insights', {}).get('wins', [])
        wins_html = "".join([f"<li style='margin: 8px 0;'>✅ {win}</li>" for win in wins])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', sans-serif; line-height: 1.6; color: #1E293B; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #7C3AED 0%, #A78BFA 100%);
                           padding: 30px; border-radius: 16px; color: white; text-align: center; }}
                .content {{ background: #F8FAFC; padding: 30px; border-radius: 16px; margin: 20px 0; }}
                .section {{ margin: 20px 0; }}
                h1 {{ margin: 0; font-size: 28px; }}
                h2 {{ color: #7C3AED; font-size: 20px; margin-top: 0; }}
                ul {{ padding-left: 20px; }}
                .button {{ background: #7C3AED; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 8px; display: inline-block;
                          margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Your Weekly Review</h1>
                    <p>Week of {review_data.get('week_start_date', '')}</p>
                </div>

                <div class="content">
                    <div class="section">
                        <h2>🎉 Key Wins This Week</h2>
                        <ul>{wins_html if wins_html else '<li>No wins recorded</li>'}</ul>
                    </div>

                    <div class="section">
                        <h2>📝 Summary</h2>
                        <p>{review_data.get('summary', 'No summary available')}</p>
                    </div>

                    <a href="https://your-app.com/review" class="button">View Full Review →</a>
                </div>

                <p style="text-align: center; color: #64748B; font-size: 12px;">
                    Powered by PARA Autopilot | Claude Haiku 4.5
                </p>
            </div>
        </body>
        </html>
        """

    def _task_reminder_template(self, user_name: str, tasks: list[Dict[str, Any]]) -> str:
        """HTML template for task reminders"""

        tasks_html = "".join([
            f"<li style='margin: 12px 0; padding: 12px; background: white; border-radius: 8px;'>"
            f"<strong>{task['title']}</strong><br>"
            f"<span style='color: #64748B; font-size: 14px;'>Due: {task.get('due_date', 'No due date')}</span>"
            f"</li>"
            for task in tasks
        ])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', sans-serif; line-height: 1.6; color: #1E293B; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #22D3EE; padding: 30px; border-radius: 16px; color: white; text-align: center; }}
                ul {{ list-style: none; padding: 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Task Reminder</h1>
                    <p>You have {len(tasks)} tasks due soon</p>
                </div>

                <div style="margin: 20px 0;">
                    <ul>{tasks_html}</ul>
                </div>

                <a href="https://your-app.com/tasks"
                   style="background: #22D3EE; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 8px; display: inline-block;">
                    View All Tasks →
                </a>
            </div>
        </body>
        </html>
        """

    def _approval_template(self, user_name: str, approval_type: str, message: str) -> str:
        """HTML template for approval requests"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', sans-serif; line-height: 1.6; color: #1E293B; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FBBF24; padding: 30px; border-radius: 16px; color: #1E293B; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 AI Suggestion Pending</h1>
                    <p>{approval_type}</p>
                </div>

                <div style="margin: 20px 0; padding: 20px; background: #F8FAFC; border-radius: 12px;">
                    <p>{message}</p>
                </div>

                <a href="https://your-app.com/approvals"
                   style="background: #FBBF24; color: #1E293B; padding: 12px 24px;
                          text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 600;">
                    Review Suggestion →
                </a>
            </div>
        </body>
        </html>
        """

# Global instance
email_service = EmailService()
