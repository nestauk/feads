from django.urls import path
from . import views

urlpatterns = [
    path('', views.active_resources, name='active_resources'),
    path('<int:id>', views.index, name='index'),
    path('process_decision/<int:id>', views.process_decision,
         name='process_decision'),
]

