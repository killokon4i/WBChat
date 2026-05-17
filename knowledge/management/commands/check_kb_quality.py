from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run quality checks on published KB articles and send review reminders'

    def add_arguments(self, parser):
        parser.add_argument('--reminders', action='store_true', help='Send review reminders')
        parser.add_argument('--check-docs', action='store_true', help='Check related documents for staleness')
        parser.add_argument('--quality', action='store_true', help='Run content quality checks')

    def handle(self, *args, **options):
        from knowledge.services import ActualizationService, QualityCheckService
        from knowledge.models import Article

        act = ActualizationService()

        if options['reminders']:
            count = act.send_review_reminders()
            self.stdout.write(self.style.SUCCESS(f'Sent {count} review reminders'))

        if options['check_docs']:
            count = act.check_related_documents()
            self.stdout.write(self.style.SUCCESS(f'Marked {count} articles as needing actualization'))

        if options['quality']:
            qc = QualityCheckService()
            articles = Article.objects.filter(status='published')
            total_issues = 0
            for article in articles:
                issues = qc.check_article(article)
                if issues:
                    total_issues += len(issues)
                    self.stdout.write(f'  {article.title}: {len(issues)} issue(s)')
                    for issue in issues:
                        self.stdout.write(f'    [{issue["level"]}] {issue["message"]}')
            self.stdout.write(self.style.SUCCESS(f'Quality check complete: {total_issues} issues in {articles.count()} articles'))

        if not any([options['reminders'], options['check_docs'], options['quality']]):
            self.stdout.write(self.style.WARNING('No action specified. Use --reminders, --check-docs, or --quality'))
