from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.EmailLogoutView.as_view(), name="logout"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("projects/<int:project_id>/prompts/", views.add_prompt, name="add_prompt"),
    path("projects/<int:project_id>/files/", views.upload_file, name="upload_file"),
    path("projects/<int:project_id>/chat/", views.chat, name="chat"),
    path("projects/<int:project_id>/chat/<int:conversation_id>/", views.chat, name="chat_conversation"),
]
