"""musicpro URL Configuration"""
from django.urls import path, include

urlpatterns = [
    path('', include('courier.urls')),
]
