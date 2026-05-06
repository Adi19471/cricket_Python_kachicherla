from django.urls import path
from . import extra_views

urlpatterns = [
    path('home/', extra_views.home_landing, name='landing_home'),
    path('contract/', extra_views.contract, name='contract'),
    path('service/', extra_views.service, name='service'),
]

