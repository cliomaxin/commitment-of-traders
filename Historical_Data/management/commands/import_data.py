from django.core.management.base import BaseCommand
from Historical_Data.models import HistoricalCotReport


class Command(BaseCommand):
    help = 'Import data from Get_Data.ExtrapolatedReport to Historical_Data.HistoricalCotReport'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            deleted_count = HistoricalCotReport.objects.all().delete()[0]
            self.stdout.write(f'Deleted {deleted_count} existing records.')

        self.stdout.write('Starting data import from Get_Data.ExtrapolatedReport...')

        try:
            imported_count, updated_count = HistoricalCotReport.import_from_extrapolated_reports()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {imported_count} new records and updated {updated_count} existing records.'
                )
            )

            # Show statistics
            total_records = HistoricalCotReport.objects.count()
            self.stdout.write(f'Total records in HistoricalCotReport: {total_records}')

            # Show category breakdown
            for category_key, category_label in HistoricalCotReport.CATEGORY_CHOICES:
                count = HistoricalCotReport.objects.filter(category=category_key).count()
                self.stdout.write(f'  {category_label}: {count} records')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during import: {e}')
            )
            raise