from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import TimeSlot
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate TimeSlots from 6AM to 10PM (30min intervals)'

    def handle(self, *args, **options):
        if TimeSlot.objects.exists():
            self.stdout.write(self.style.SUCCESS('TimeSlots already exist. Skipping.'))
            return

        start_time = datetime.strptime('06:00', '%H:%M').time()
        end_time = datetime.strptime('22:00', '%H:%M').time()
        current = start_time

        while current <= end_time:
            end = (datetime.combine(datetime.today(), current) + timedelta(minutes=30)).time()
            TimeSlot.objects.create(start_time=current, end_time=end)
            current = end

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {TimeSlot.objects.count()} TimeSlots')
        )

