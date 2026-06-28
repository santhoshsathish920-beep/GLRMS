from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run a full automated land monitoring scan using GEE + ML.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the scan without updating the database.',
        )

    def handle(self, *args, **options):
        from lands.services import run_automated_monitoring

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n╔══════════════════════════════════════════════╗\n'
            '║   GLRMS Automated Land Monitoring Scan       ║\n'
            '╚══════════════════════════════════════════════╝\n'
        ))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE: No database changes will be made.\n'))
            return

        self.stdout.write('  → Fetching Sentinel-2 data from Google Earth Engine...')
        self.stdout.write('  → Running NDVI-based change detection...')
        self.stdout.write('  → Performing spatial overlay with land parcels...\n')

        success = run_automated_monitoring()

        if success:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ Monitoring scan completed successfully! '
                'Check the dashboard for updated alerts.\n'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                '\n✗ Scan failed. Check logs for details.\n'
                '  Common causes:\n'
                '    - Missing gee_key.json in project root\n'
                '    - No land parcels with coordinates in the database\n'
                '    - GEE authentication error\n'
            ))
