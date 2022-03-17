import smtplib
import email
from flask import current_app


class Email:
    def __init__(self, to='', text_body='', html_body='', debug=False) -> None:
        self.debug = debug
        self.msg = email.message.EmailMessage()
        self.domain = 'mail.warwickjudo.com'
        self.user = current_app.config['SMTP_USER']
        self.password = current_app.config['SMTP_PASS']
        self.msg['From'] = 'noreply@' + self.domain
        self.msg['To'] = to
        self.msg['Subject'] = 'Password Reset for Warwick Judo & BJJ'
        self.msg.add_alternative(text_body)
        self.msg.add_alternative(html_body, subtype='html')

        if debug:
            print(f'msg: {self.msg}\n\nUser: {self.user}\nPass: {self.password}\n')

        
    def send_message(self):
        session = smtplib.SMTP('email-smtp.eu-west-2.amazonaws.com')

        if self.debug:
            session.set_debuglevel(2)

        session.ehlo()
        session.starttls()
        session.login(self.user, self.password)
        session.send_message(self.msg)
        session.quit()