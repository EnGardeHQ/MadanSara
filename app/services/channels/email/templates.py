"""Email template management and rendering."""

from typing import Dict, List, Optional, Any
from jinja2 import Environment, BaseLoader, TemplateNotFound
from datetime import datetime


class EmailTemplateManager:
    """Manages email templates and rendering."""

    def __init__(self):
        self.env = Environment(loader=BaseLoader())

    def render_template(
        self,
        template_str: str,
        data: Dict[str, Any],
    ) -> str:
        """
        Render Jinja2 template with data.

        Args:
            template_str: Template string
            data: Variables for rendering

        Returns:
            Rendered template
        """
        template = self.env.from_string(template_str)
        return template.render(**data)

    def get_newsletter_template(self, style: str = "modern") -> Dict[str, str]:
        """
        Get newsletter HTML template.

        Args:
            style: Template style (modern, classic, minimal)

        Returns:
            Template dict with HTML and text versions
        """
        templates = {
            "modern": {
                "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{subject}}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4A90E2; color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; background: #ffffff; }
        .cta-button { display: inline-block; padding: 12px 30px; background: #4A90E2;
                      color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{header_title}}</h1>
        </div>
        <div class="content">
            <p>Hi {{name}},</p>
            {{content}}
            {% if cta_url %}
            <p style="text-align: center;">
                <a href="{{cta_url}}" class="cta-button">{{cta_text}}</a>
            </p>
            {% endif %}
        </div>
        <div class="footer">
            <p>© {{year}} En Garde. All rights reserved.</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
                """,
                "text": """
Hi {{name}},

{{content_text}}

{% if cta_url %}
{{cta_text}}: {{cta_url}}
{% endif %}

© {{year}} En Garde
Unsubscribe: {{unsubscribe_url}}
                """
            },
            "minimal": {
                "html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p>Hi {{name}},</p>
    {{content}}
    {% if cta_url %}
    <p><a href="{{cta_url}}" style="color: #4A90E2;">{{cta_text}}</a></p>
    {% endif %}
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
    <p style="font-size: 12px; color: #666;">
        <a href="{{unsubscribe_url}}">Unsubscribe</a>
    </p>
</body>
</html>
                """,
                "text": """
Hi {{name}},

{{content_text}}

{% if cta_url %}{{cta_text}}: {{cta_url}}{% endif %}

Unsubscribe: {{unsubscribe_url}}
                """
            }
        }

        return templates.get(style, templates["modern"])

    def get_transactional_template(self, template_type: str) -> Dict[str, str]:
        """
        Get transactional email template.

        Args:
            template_type: welcome, confirmation, reset_password, etc.

        Returns:
            Template dict
        """
        templates = {
            "welcome": {
                "subject": "Welcome to {{company_name}}!",
                "html": """
<p>Hi {{name}},</p>
<p>Welcome to {{company_name}}! We're excited to have you on board.</p>
<p>Here's what you can do next:</p>
<ul>
    <li>Complete your profile</li>
    <li>Explore our features</li>
    <li>Connect with our team</li>
</ul>
<p><a href="{{dashboard_url}}">Get Started</a></p>
                """,
                "text": "Hi {{name}},\n\nWelcome to {{company_name}}!\n\nGet started: {{dashboard_url}}"
            },
            "order_confirmation": {
                "subject": "Order Confirmation #{{order_number}}",
                "html": """
<p>Hi {{name}},</p>
<p>Thank you for your order! Your order #{{order_number}} has been confirmed.</p>
<h3>Order Details:</h3>
{{order_details}}
<p>Estimated delivery: {{delivery_date}}</p>
<p><a href="{{tracking_url}}">Track Your Order</a></p>
                """,
                "text": "Hi {{name}},\n\nOrder #{{order_number}} confirmed.\n\nTrack: {{tracking_url}}"
            },
            "password_reset": {
                "subject": "Reset Your Password",
                "html": """
<p>Hi {{name}},</p>
<p>You requested to reset your password. Click the link below:</p>
<p><a href="{{reset_url}}">Reset Password</a></p>
<p>This link expires in 24 hours.</p>
<p>If you didn't request this, please ignore this email.</p>
                """,
                "text": "Hi {{name}},\n\nReset your password: {{reset_url}}\n\nExpires in 24 hours."
            }
        }

        return templates.get(template_type, {})

    def create_personalized_content(
        self,
        base_content: str,
        recipient_data: Dict[str, Any],
        campaign_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create personalized email content.

        Args:
            base_content: Base content with placeholders
            recipient_data: Recipient-specific data
            campaign_data: Campaign-specific data

        Returns:
            Personalized content
        """
        # Merge data
        data = {
            "name": recipient_data.get("name", "Valued Customer"),
            "email": recipient_data.get("email", ""),
            "company": recipient_data.get("company", ""),
            "year": datetime.now().year,
        }

        if campaign_data:
            data.update(campaign_data)

        # Render template
        return self.render_template(base_content, data)

    def add_tracking_pixels(
        self,
        html_content: str,
        message_id: str,
    ) -> str:
        """
        Add tracking pixel to HTML email.

        Args:
            html_content: HTML content
            message_id: Message ID for tracking

        Returns:
            HTML with tracking pixel
        """
        tracking_pixel = f'<img src="https://track.engarde.com/pixel/{message_id}" width="1" height="1" alt="" />'

        # Insert before closing body tag
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", f"{tracking_pixel}</body>")
        else:
            html_content += tracking_pixel

        return html_content

    def add_utm_parameters(
        self,
        url: str,
        campaign: str,
        source: str = "email",
        medium: str = "newsletter",
    ) -> str:
        """
        Add UTM parameters to URL for tracking.

        Args:
            url: Base URL
            campaign: Campaign name
            source: Traffic source
            medium: Marketing medium

        Returns:
            URL with UTM parameters
        """
        separator = "&" if "?" in url else "?"

        utm_params = f"utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"

        return f"{url}{separator}{utm_params}"

    def validate_template(self, template_str: str) -> Dict[str, Any]:
        """
        Validate template syntax.

        Args:
            template_str: Template string to validate

        Returns:
            Validation result
        """
        try:
            template = self.env.from_string(template_str)
            # Try rendering with empty context
            template.render()

            return {
                "valid": True,
                "errors": []
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)]
            }

    def extract_variables(self, template_str: str) -> List[str]:
        """
        Extract variables from template.

        Args:
            template_str: Template string

        Returns:
            List of variable names
        """
        try:
            template = self.env.from_string(template_str)
            # Get undeclared variables
            from jinja2 import meta
            parsed = self.env.parse(template_str)
            variables = meta.find_undeclared_variables(parsed)

            return sorted(list(variables))

        except:
            return []
