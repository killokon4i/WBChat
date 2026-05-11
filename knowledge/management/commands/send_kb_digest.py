from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send Knowledge Base digest notifications and emails to subscribers'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Period in days (default: 7)')
        parser.add_argument('--email', action='store_true', help='Also send email digests')

    def handle(self, *args, **options):
        from knowledge.services import DigestService
        svc = DigestService()
        days = options['days']

        count = svc.send_digest_notifications(period_days=days)
        self.stdout.write(self.style.SUCCESS(f'Sent {count} digest notifications (period: {days} days)'))

        if options['email']:
            email_count = svc.send_email_digest(period_days=days)
            self.stdout.write(self.style.SUCCESS(f'Sent {email_count} digest emails'))
