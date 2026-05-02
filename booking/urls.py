from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('book/', views.book_slot, name='book_slot'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('history/', views.history, name='history'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:booking_id>/reschedule/', views.reschedule_booking, name='reschedule_booking'),
    path('api/booked-slots/<str:date_str>/', views.api_booked_slots, name='api_booked_slots'),
    path('upcoming/', views.upcoming_bookings, name='upcoming_bookings'),
    path('profile/', views.my_profile, name='my_profile'),
    # Admin endpoints
    path('admin/booking/<int:booking_id>/modify-amount/', views.modify_booking_amount, name='modify_booking_amount'),
    path('admin/booking/<int:booking_id>/modify-timing/', views.modify_booking_timing, name='modify_booking_timing'),
]
