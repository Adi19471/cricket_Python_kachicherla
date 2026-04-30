from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('register/', views.register, name="register"),
    path('login/', views.login_view, name="login_view"),
    path('logout/', views.logout_view, name="logout"),
    path('api/booked-slots/<str:date_str>/', views.api_booked_slots, name="api_booked_slots"),
    path('book/', views.book_slot, name="book"),
    path('payment-success/', views.payment_success, name="payment_success"),
    path('history/', views.history, name="history"),
    path('booking/<int:booking_id>/', views.booking_detail, name="booking_detail"),
]
