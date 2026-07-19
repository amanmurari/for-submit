from django.contrib import admin
from .models import Conversation, Message, Project, ProjectFile, Prompt, User

admin.site.register([User, Project, Prompt, Conversation, Message, ProjectFile])
