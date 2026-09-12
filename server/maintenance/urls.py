from django.urls import path
from . import views
urlpatterns=[path("routing/",views.routing),path("status/",views.status)]
