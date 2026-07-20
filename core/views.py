from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from httpcore import request
from .forms import EmailAuthenticationForm, ProjectForm, PromptForm, RegistrationForm
from .models import Conversation, Message, Project, ProjectFile, Prompt
from .services import KnowledgeBaseError, LLMServiceError, generate_response, index_file


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form=RegistrationForm()
    if request.method=="POST":
        form=RegistrationForm(request.POST)
        if form.is_valid():
            user=form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("dashboard")
        else:
            messages.error(request, "Unsuccessful registration. Invalid information.")
    return render(request, "core/register.html", {"form": form})


class EmailLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = EmailAuthenticationForm


class EmailLogoutView(LogoutView):
    pass



@login_required
def dashboard(request):
    form=ProjectForm()
    if request.method == "POST":
        form=ProjectForm(request.POST)
        if form.is_valid():
            project=form.save(commit=False)
            project.owner=request.user
            project.save()
            messages.success(request, "Project created successfully.")
            return redirect("project_detail", project_id=project.id)
        else:
            messages.error(request, "Failed to create project. Please check the form for errors.")
    return render(request, "core/dashboard.html", {"projects": request.user.projects.all(), "form": form})




def owned_project(request, project_id):
    return get_object_or_404(Project, id=project_id, owner=request.user)


@login_required
def project_detail(request, project_id):
    project = owned_project(request, project_id)
    return render(request, "core/project_detail.html", {"project": project, "prompt_form": PromptForm()})


@login_required
@require_POST
def add_prompt(request,project_id):
    owned=owned_project(request,project_id)
    form=PromptForm(request.POST)
    if form.is_valid():
        prpt=form.save(commit=False)
        prpt.project=owned
        prpt.save()
    else:
        messages.error(request, "Please correct the prompt form.")
    return redirect("project_detail", project_id=owned.id)




@login_required
@require_POST
def upload_file(request, project_id):
    project = owned_project(request, project_id)
    is_async = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    uploaded = request.FILES.get("file")
    if not uploaded:
        if is_async:
            return JsonResponse({"ok": False, "error": "Choose a file first."}, status=400)
        messages.error(request, "Choose a file first.")
    elif uploaded.size > 20 * 1024 * 1024:
        if is_async:
            return JsonResponse({"ok": False, "error": "Files must be 20 MB or smaller."}, status=400)
        messages.error(request, "Files must be 20 MB or smaller.")
    else:
        content = uploaded.read()
        # Save the Django record quickly; embedding can take longer and must not
        # keep a SQLite transaction open.
        with transaction.atomic():
            uploaded.seek(0)
            project_file = ProjectFile.objects.create(project=project, file=uploaded, original_name=uploaded.name)
        try:
            chunk_count = index_file(project_file, content)
        except KnowledgeBaseError as exc:
            project_file.delete()
            if is_async:
                return JsonResponse({"ok": False, "error": str(exc)}, status=502)
            messages.error(request, str(exc))
        else:
            if is_async:
                return JsonResponse({
                    "ok": True,
                    "name": project_file.original_name,
                    "url": project_file.file.url,
                    "chunk_count": chunk_count,
                })
            messages.success(request, f"File added to the knowledge base ({chunk_count} searchable sections).")
    return redirect("project_detail", project_id=project.id)


@login_required
@require_http_methods(["GET", "POST"])
def chat(request, project_id, conversation_id=None):
    project = owned_project(request, project_id)
    conversation = None
    selected_prompt = None
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id, project=project)
    selected_prompt_id = request.POST.get("prompt_id") if request.method == "POST" else request.GET.get("prompt")
    if selected_prompt_id:
        selected_prompt = project.prompts.filter(id=selected_prompt_id).first()
    if request.method == "POST":
        is_async = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        use_knowledge_base = request.POST.get("use_knowledge_base") == "on"
        content = request.POST.get("message", "").strip()
        if not content:
            messages.error(request, "Enter a message.")
        else:
            # Keep this write transaction short. Calling Groq/Cohere while a SQLite
            # transaction is open can block all other requests from writing.
            with transaction.atomic():
                conversation = conversation or Conversation.objects.create(project=project, title=content[:80])
                Message.objects.create(conversation=conversation, role=Message.Role.USER, content=content)
            try:
                answer = generate_response(
                    project,
                    conversation.messages.all(),
                    selected_prompt=selected_prompt,
                    use_knowledge_base=use_knowledge_base,
                )
            except LLMServiceError as exc:
                Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=str(exc))
                conversation.save(update_fields=["updated_at"])
                if is_async:
                    return JsonResponse({
                        "ok": False,
                        "answer": str(exc),
                        "chat_url": reverse("chat_conversation", args=[project.id, conversation.id]),
                    })
                messages.error(request, "Your message was saved, but the AI response failed.")
                return redirect("chat_conversation", project_id=project.id, conversation_id=conversation.id)
            else:
                Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=answer)
                conversation.save(update_fields=["updated_at"])
                if is_async:
                    return JsonResponse({
                        "ok": True,
                        "answer": answer,
                        "chat_url": reverse("chat_conversation", args=[project.id, conversation.id]),
                    })
                return redirect("chat_conversation", project_id=project.id, conversation_id=conversation.id)
    if conversation is None:
        conversation = project.conversations.first()
    return render(request, "core/chat.html", {
        "project": project,
        "conversation": conversation,
        "conversations": project.conversations.all(),
        "prompts": project.prompts.all(),
        "selected_prompt": selected_prompt,
    })







