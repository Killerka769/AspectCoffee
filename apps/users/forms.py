from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.core.mail import send_mail

class AspectCoffeePasswordResetForm(PasswordResetForm):
    def save(self, domain_override=None, request=None, **kwargs):
        # Ссылка в письме берётся с адреса, по которому человек открыл сайт.
        if not domain_override and request is not None:
            domain_override = request.get_host()
        return super().save(domain_override=domain_override, request=request, **kwargs)

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context).strip()
        text_body = render_to_string(email_template_name, context)
        html_body = render_to_string("emails/password_reset_email.html", context)
        send_mail(
            subject=subject,
            message=text_body,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_body,
            fail_silently=False,
        )
