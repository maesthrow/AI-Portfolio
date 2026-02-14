"""Email templates for CV sending."""

CV_EMAIL_SUBJECT = "Резюме | Dmitry — Backend & AI Developer"

CV_EMAIL_BODY_HTML = """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
    <p>Здравствуйте!</p>
    <p>Вы запросили резюме Дмитрия через AI-Portfolio.</p>
    <p>Резюме прикреплено к этому письму в формате PDF.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #888; font-size: 12px;">
        Отправлено автоматически через
        <a href="https://ai-portfolio.dev" style="color: #888;">AI-Portfolio</a><br>
        Если вы не запрашивали это письмо, просто проигнорируйте его.
    </p>
</body>
</html>
"""

CV_EMAIL_BODY_PLAIN = """\
Здравствуйте!

Вы запросили резюме Дмитрия через AI-Portfolio.
Резюме прикреплено к этому письму в формате PDF.

---
Отправлено автоматически через AI-Portfolio.
Если вы не запрашивали это письмо, просто проигнорируйте его.
"""
