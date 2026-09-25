from django.urls import path
from . import views

urlpatterns = [
    path('capabilities/',views.capabilities), path('projects/',views.projects),
    path('templates/',views.templates), path('templates/<uuid:template_id>/',views.template_detail),
    path('projects/<uuid:pk>/',views.project_detail), path('projects/<uuid:pk>/edit/',views.edit),
    path('projects/<uuid:pk>/revisions/<int:revision_id>/restore/',views.restore),
    path('projects/<uuid:pk>/revisions/<int:revision_id>/download/',views.download),
    path('projects/<uuid:pk>/revisions/<int:revision_id>/pages/<int:page>/',views.preview),
    path('projects/<uuid:pk>/chat/',views.chat), path('projects/<uuid:pk>/plans/<int:message_id>/apply/',views.apply_plan),
    path('projects/<uuid:pk>/jobs/<uuid:job_id>/cancel/',views.cancel_job),
    path('projects/<uuid:pk>/references/',views.add_reference),
    path('projects/<uuid:pk>/references/<uuid:reference_id>/',views.reference_detail),
    path('projects/<uuid:pk>/handoff/',views.handoff),
]
