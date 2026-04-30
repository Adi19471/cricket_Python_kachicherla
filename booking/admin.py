from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import TimeSlot, Booking, UserProfile


admin.site.site_header = "🏏 CRICKET BOOKING"
admin.site.site_title = "Cricket Admin"
admin.site.index_title = "Welcome to Cricket Booking Dashboard"


# ✅ TIMESLOT ADMIN
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'is_booked')  # ✅ show booked status
    list_filter = ('is_booked',)
    list_editable = ('is_booked',)  # ✅ admin can manually block/unblock
    list_per_page = 20


# ✅ INLINE SLOT DISPLAY IN BOOKING
class SlotInline(admin.TabularInline):
    model = Booking.slots.through
    extra = 0


# ✅ BOOKING ADMIN
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'date',
        'slots_count',
        'total_amount',
        'is_paid',
        'status',
        'created_at'
    )

    list_filter = ('is_paid', 'status', 'date', 'created_at')
    search_fields = ('user__username', 'razorpay_order_id')

    readonly_fields = ('created_at',)
    filter_horizontal = ('slots',)  # ✅ better UI for selecting slots
    inlines = [SlotInline]

    list_editable = ('total_amount', 'status')  # ✅ admin can change directly

    actions = ['mark_as_completed_action']

    # ✅ SLOT COUNT
    def slots_count(self, obj):
        return obj.slots.count()
    slots_count.short_description = 'Slots Count'

    # ✅ SAVE LOGIC (AUTO TOTAL)
    def save_model(self, request, obj, form, change):
        if not obj.total_amount:
            obj.total_amount = obj.amount * obj.slots.count()
        super().save_model(request, obj, form, change)

    # ✅ ADMIN ACTION → COMPLETE BOOKING
    def mark_as_completed_action(self, request, queryset):
        for booking in queryset:
            if booking.is_paid:
                booking.status = 'completed'
                booking.save()

                # 🔒 BLOCK SLOTS
                for slot in booking.slots.all():
                    slot.is_booked = True
                    slot.save()

        self.message_user(request, "Selected bookings marked as completed.")
    mark_as_completed_action.short_description = "Mark selected bookings as completed"


# ✅ USER PROFILE ADMIN
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'amount')
    search_fields = ('user__username', 'phone_number')
    list_filter = ('amount',)


# ✅ CUSTOM USER ADMIN
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')