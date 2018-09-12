from django.urls import path
from . import views

urlpatterns = [
    path('', views.active_resources, name='active_resources'),
    path('<str:title>', views.index, name='index'),
    path('process_decision/<str:title>', views.process_decision,
         name='process_decision'),
]
