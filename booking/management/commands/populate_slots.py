from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import TimeSlot
from datetime import datetime, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Populate TimeSlots for 24 hours (00:00 - 23:00, hourly slots)'

    def handle(self, *args, **options):
        if TimeSlot.objects.exists():
            TimeSlot.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing TimeSlots deleted. Creating new ones.'))

        # Default price per hour slot - use string for Decimal
        DEFAULT_PRICE = Decimal('300')  # Change this value as needed

        # Create 24 hourly slots from 00:00 to 23:00
        for hour in range(24):
            start_time = datetime.strptime(f'{hour:02d}:00', '%H:%M').time()
            end_time = datetime.strptime(f'{hour:02d}:00', '%H:%M').time()
            end_time = (datetime.combine(datetime.today(), start_time) + timedelta(hours=1)).time()
            TimeSlot.objects.create(start_time=start_time, end_time=end_time, isa=DEFAULT_PRICE)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {TimeSlot.objects.count()} TimeSlots (24-hour day)')
        )
