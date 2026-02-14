"""Email templates for CV sending."""

CV_EMAIL_SUBJECT = "Резюме | Дмитрий Каргин — AI Engineer"


def cv_email_body_html(site_url: str) -> str:
    """HTML body for CV email. *site_url* — full URL like ``https://example.com``."""
    link = (
        f'<a href="{site_url}" style="color: #00e5ff;">AI-Portfolio</a>'
        if site_url
        else "AI-Portfolio"
    )
    footer_link = (
        f'<a href="{site_url}" style="color: #888;">AI-Portfolio</a>'
        if site_url
        else "AI-Portfolio"
    )
    return f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
    <p>Здравствуйте!<br>
    На связи ИИ-ассистент Дмитрия!</p>
    <p>Вы запросили резюме на сайте {link}.</p>
    <p>Резюме прикреплено к этому письму в формате PDF.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #888; font-size: 12px;">
        Отправлено автоматически через {footer_link}<br>
        Если вы не запрашивали это письмо, просто проигнорируйте его.
    </p>
</body>
</html>
"""


def cv_email_body_plain(site_url: str) -> str:
    """Plain-text body for CV email."""
    label = f"AI-Portfolio ({site_url})" if site_url else "AI-Portfolio"
    return f"""\
Здравствуйте!
На связи ИИ-ассистент Дмитрия!

Вы запросили резюме на сайте {label}.
Резюме прикреплено к этому письму в формате PDF.

---
Отправлено автоматически через {label}.
Если вы не запрашивали это письмо, просто проигнорируйте его.
"""
