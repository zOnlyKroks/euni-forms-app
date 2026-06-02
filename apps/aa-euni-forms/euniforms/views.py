"""Views for the EVE Uni Forms app."""

# Standard Library
import csv
import logging

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.utils.translation import gettext as _

# Alliance Auth
from allianceauth.notifications import notify

# AA EVE Uni Forms
from euniforms.forms import DynamicFillForm, FormFieldModelForm, FormModelForm
from euniforms.models import Form, FormAnswer, FormField, FormResponse, FormCollaborator
from euniforms.services import DiscordWebhookService
from euniforms.logging_utils import app_logger, log_user_action, log_permission_denied

logger = logging.getLogger(__name__)


def _has_app_access(user) -> bool:
    """Whether the user may use the Forms app at all."""
    return user.has_perm("euniforms.basic_access") or user.has_perm(
        "euniforms.manage_forms"
    )


def _main_character(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "main_character", None)


# ---------------------------------------------------------------------------
# Member-facing views
# ---------------------------------------------------------------------------


@login_required
def index(request):
    """Landing page: forms the user can fill, review, or manage."""
    user = request.user
    if not _has_app_access(user):
        log_permission_denied(user, "access_forms_app", "euniforms")
        raise PermissionDenied

    can_manage = user.has_perm("euniforms.manage_forms")
    search_query = request.GET.get("search", "").strip()

    open_forms = Form.objects.filter(status=Form.Status.OPEN).prefetch_related(
        "restricted_groups"
    )

    # Apply search filtering if query exists
    if search_query:
        from django.db.models import Q
        open_forms = open_forms.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    fillable_forms = [form for form in open_forms if form.is_eligible(user)]
    submitted_ids = set(
        FormResponse.objects.filter(
            user=user, form__in=fillable_forms
        ).values_list("form_id", flat=True)
    )

    # Check which forms allow resubmission for this user
    resubmission_allowed_ids = set()
    for form in fillable_forms:
        if form.allows_resubmission(user):
            resubmission_allowed_ids.add(form.id)

    if can_manage:
        managed_forms = Form.objects.all()
        # Apply search filtering to managed forms too
        if search_query:
            from django.db.models import Q
            managed_forms = managed_forms.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )

        reviewable_forms = Form.objects.none()
    else:
        # Include forms where user is a collaborator or has viewer rights
        from django.db.models import Q
        managed_forms = Form.objects.filter(
            Q(collaborators__user=user)
        ).distinct()
        reviewable_forms = Form.objects.filter(
            viewer_groups__in=user.groups.all()
        ).distinct()

        # Apply search filtering to both managed and reviewable forms
        if search_query:
            managed_forms = managed_forms.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )
            reviewable_forms = reviewable_forms.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )

    context = {
        "fillable_forms": fillable_forms,
        "submitted_ids": submitted_ids,
        "resubmission_allowed_ids": resubmission_allowed_ids,
        "can_manage": can_manage,
        "managed_forms": managed_forms,
        "reviewable_forms": reviewable_forms,
        "search_query": search_query,
    }
    return render(request, "euniforms/index.html", context)


@login_required
def form_fill(request, form_pk):
    """Render and accept a submission for a single form."""
    user = request.user
    if not _has_app_access(user):
        raise PermissionDenied

    form_obj = get_object_or_404(Form, pk=form_pk)
    can_manage = user.has_perm("euniforms.manage_forms")

    if not form_obj.is_eligible(user):
        raise PermissionDenied

    already_submitted = form_obj.has_response_from(user)
    blocked_reason = None
    is_draft_preview = form_obj.status == Form.Status.DRAFT

    if not can_manage and not is_draft_preview:
        can_submit, limit_reason = form_obj.check_submission_limit(user)
        if not can_submit:
            blocked_reason = limit_reason

    if form_obj.status == Form.Status.CLOSED:
        blocked_reason = _("This form is closed and no longer accepting responses.")

    main_character = _main_character(user)

    if request.method == "POST" and not blocked_reason and not is_draft_preview:
        fill_form = DynamicFillForm(request.POST, form_obj=form_obj, user=user)
        if main_character is None:
            messages.error(
                request,
                _(
                    "You need a main character set on your account before you "
                    "can submit forms."
                ),
            )
        elif fill_form.is_valid():
            response = _save_response(form_obj, user, main_character, fill_form)

            # Log form submission
            app_logger.form_submitted(
                form_id=form_obj.pk,
                response_id=response.pk,
                user_id=user.id,
                submitter_name=response.submitter_display,
                form_title=form_obj.title
            )

            messages.success(
                request, _("Your response has been submitted. Thank you!")
            )
            return redirect("euniforms:form_submitted", form_pk=form_obj.pk)
    else:
        fill_form = DynamicFillForm(form_obj=form_obj, user=user)

    context = {
        "form_obj": form_obj,
        "fill_form": fill_form,
        "blocked_reason": blocked_reason,
        "can_manage": can_manage,
        "is_draft_preview": is_draft_preview,
    }
    return render(request, "euniforms/form_fill.html", context)


@transaction.atomic
def _save_response(form_obj, user, main_character, fill_form):
    response = FormResponse.objects.create(
        form=form_obj,
        user=user,
        main_character_id=getattr(main_character, "character_id", None),
        main_character_name=getattr(main_character, "character_name", "") or "",
    )
    FormAnswer.objects.bulk_create(
        FormAnswer(
            response=response,
            field=question,
            field_label=question.label,
            field_type=question.field_type,
            value=value,
        )
        for question, value in fill_form.iter_answers()
    )
    if form_obj.notify_on_submit:
        _notify_viewers(form_obj, response)
    if form_obj.discord_webhook_url:
        _notify_discord(form_obj, response)
    return response


def _notify_viewers(form_obj, response):
    title = _("New form response: %(title)s") % {"title": form_obj.title}
    message = _('%(submitter)s submitted a response to "%(title)s".') % {
        "submitter": response.submitter_display,
        "title": form_obj.title,
    }
    recipients = form_obj.notification_recipients()
    if response.user_id:
        recipients = recipients.exclude(pk=response.user_id)
    for recipient in recipients:
        notify.info(recipient, title, message)


def _notify_discord(form_obj, response):
    """Send form response to Discord webhook with structured logging."""
    if not form_obj.discord_webhook_url:
        return True

    try:
        success = DiscordWebhookService.send_form_response(
            form_obj.discord_webhook_url, form_obj, response
        )

        # Use structured logging for webhook events
        app_logger.discord_webhook_sent(
            form_id=form_obj.pk,
            response_id=response.pk,
            webhook_url=form_obj.discord_webhook_url,
            success=success,
            form_title=form_obj.title,
            submitter=response.submitter_display
        )

        return success

    except Exception as e:
        # Log webhook failure with full context
        app_logger.error(
            f"Discord webhook exception for form {form_obj.pk}: {e}",
            exc_info=True,
            event_type="discord_webhook_error",
            form_id=form_obj.pk,
            form_title=form_obj.title,
            webhook_url=form_obj.discord_webhook_url[:50] + '...' if form_obj.discord_webhook_url else None,
            response_id=response.pk,
            submitter=response.submitter_display
        )
        return False


@login_required
def form_submitted(request, form_pk):
    """Thank-you page after a successful submission."""
    if not _has_app_access(request.user):
        raise PermissionDenied
    form_obj = get_object_or_404(Form, pk=form_pk)
    return render(request, "euniforms/form_submitted.html", {"form_obj": form_obj})


# ---------------------------------------------------------------------------
# Form management (manage_forms permission)
# ---------------------------------------------------------------------------


@login_required
@permission_required("euniforms.manage_forms", raise_exception=True)
def form_create(request):
    if request.method == "POST":
        form = FormModelForm(request.POST)
        if form.is_valid():
            form_obj = form.save(commit=False)
            form_obj.created_by = request.user
            form_obj.save()
            form.save_m2m()

            # Log form creation
            app_logger.form_created(
                form_id=form_obj.pk,
                title=form_obj.title,
                created_by_id=request.user.id,
                status=form_obj.status
            )

            messages.success(request, _("Form created. Now add some questions."))
            return redirect("euniforms:manage_fields", form_pk=form_obj.pk)
    else:
        form = FormModelForm()
    return render(
        request, "euniforms/manage/form_form.html", {"form": form, "is_create": True}
    )


@login_required
def form_edit(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = FormModelForm(request.POST, instance=form_obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("Form updated."))
            return redirect("euniforms:manage_fields", form_pk=form_obj.pk)
    else:
        form = FormModelForm(instance=form_obj)
    return render(
        request,
        "euniforms/manage/form_form.html",
        {"form": form, "form_obj": form_obj, "is_create": False},
    )


@login_required
def form_delete(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    if request.method == "POST":
        title = form_obj.title
        form_obj.delete()
        messages.success(request, _('Form "%(title)s" deleted.') % {"title": title})
        return redirect("euniforms:index")
    return render(
        request, "euniforms/manage/form_confirm_delete.html", {"form_obj": form_obj}
    )


@login_required
def manage_fields(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    fields = form_obj.fields.all().prefetch_related("choices")
    return render(
        request,
        "euniforms/manage/manage_fields.html",
        {"form_obj": form_obj, "fields": fields},
    )


@login_required
def field_create(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    if request.method == "POST":
        field_form = FormFieldModelForm(request.POST)
        if field_form.is_valid():
            question = field_form.save(commit=False)
            question.form = form_obj
            question.order = (
                form_obj.fields.aggregate(value=Max("order"))["value"] or 0
            ) + 1
            question.save()
            field_form.save_choices(question)
            messages.success(request, _("Question added."))
            return redirect("euniforms:manage_fields", form_pk=form_obj.pk)
    else:
        field_form = FormFieldModelForm()
    return render(
        request,
        "euniforms/manage/field_form.html",
        {"field_form": field_form, "form_obj": form_obj, "is_create": True},
    )


@login_required
def field_edit(request, field_pk):
    question = get_object_or_404(FormField, pk=field_pk)
    form_obj = question.form
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    if request.method == "POST":
        field_form = FormFieldModelForm(request.POST, instance=question)
        if field_form.is_valid():
            question = field_form.save()
            field_form.save_choices(question)
            messages.success(request, _("Question updated."))
            return redirect("euniforms:manage_fields", form_pk=form_obj.pk)
    else:
        field_form = FormFieldModelForm(instance=question)
    return render(
        request,
        "euniforms/manage/field_form.html",
        {
            "field_form": field_form,
            "form_obj": form_obj,
            "question": question,
            "is_create": False,
        },
    )


@login_required
def field_delete(request, field_pk):
    question = get_object_or_404(FormField, pk=field_pk)
    form_obj = question.form
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    if request.method == "POST":
        question.delete()
        messages.success(request, _("Question removed."))
    return redirect("euniforms:manage_fields", form_pk=form_obj.pk)


@login_required
def field_move(request, field_pk, direction):
    question = get_object_or_404(FormField, pk=field_pk)
    form_obj = question.form
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied
    fields = list(form_obj.fields.all())
    index = next((i for i, f in enumerate(fields) if f.pk == question.pk), None)
    if index is not None:
        swap_index = index - 1 if direction == "up" else index + 1
        if 0 <= swap_index < len(fields):
            fields[index], fields[swap_index] = fields[swap_index], fields[index]
            for position, field in enumerate(fields):
                field.order = position
            FormField.objects.bulk_update(fields, ["order"])
    return redirect("euniforms:manage_fields", form_pk=form_obj.pk)


# ---------------------------------------------------------------------------
# Collaborator management
# ---------------------------------------------------------------------------


@login_required
def collaborators_list(request, form_pk):
    """List and manage collaborators for a form."""
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied

    collaborators = form_obj.collaborators.select_related("user").order_by("added_at")

    context = {
        "form_obj": form_obj,
        "collaborators": collaborators,
    }
    return render(request, "euniforms/manage/collaborators_list.html", context)


@login_required
def collaborator_add(request, form_pk):
    """Add a new collaborator to a form."""
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if not username:
            messages.error(request, _("Please enter a username."))
            return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

        # Try to find user by username first
        user = None
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            # If not found by username, try to find by EVE character name
            # Search through all users' character ownerships
            for potential_user in User.objects.all():
                # Check if this user has any characters with the given name
                try:
                    # Check user's main character
                    main_char = _main_character(potential_user)
                    if main_char and hasattr(main_char, 'character_name'):
                        if main_char.character_name.lower() == username.lower():
                            user = potential_user
                            break

                    # Check user's character ownerships if they exist
                    if hasattr(potential_user, 'character_ownerships'):
                        for ownership in potential_user.character_ownerships.all():
                            if hasattr(ownership, 'character'):
                                char = ownership.character
                                if hasattr(char, 'character_name') and char.character_name.lower() == username.lower():
                                    user = potential_user
                                    break
                                # Some systems might use 'name' instead
                                if hasattr(char, 'name') and char.name.lower() == username.lower():
                                    user = potential_user
                                    break
                        if user:  # Found the user, break out of outer loop
                            break
                except (AttributeError, TypeError):
                    continue  # Skip this user if there's any issue accessing their characters

        if not user:
            # Add some debugging info for the user
            debug_info = f"Searched for: {username}. "
            if User.objects.count() > 0:
                debug_info += f"Found {User.objects.count()} users total. "
                # Check if we can find any users with characters
                users_with_main_chars = 0
                for u in User.objects.all()[:10]:  # Check first 10 users only
                    main_char = _main_character(u)
                    if main_char and hasattr(main_char, 'character_name'):
                        users_with_main_chars += 1
                debug_info += f"Sample users with main characters: {users_with_main_chars}/10. "

            messages.error(request, _('User or character "%(username)s" not found. %(debug)s') % {
                "username": username,
                "debug": debug_info
            })
            return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

        # Check if user is already a collaborator
        if form_obj.collaborators.filter(user=user).exists():
            messages.error(request, _('User "%(username)s" is already a collaborator on this form.') % {"username": username})
            return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

        # Check if user is the form creator
        if form_obj.created_by == user:
            messages.error(request, _('Cannot add the form creator as a collaborator.'))
            return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

        # Create the collaborator
        FormCollaborator.objects.create(
            form=form_obj,
            user=user,
            added_by=request.user,
        )

        messages.success(request, _('User "%(username)s" has been added as a collaborator.') % {"username": username})
        return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

    return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)


@login_required
def collaborator_remove(request, form_pk, user_id):
    """Remove a collaborator from a form."""
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_edit_form(request.user):
        raise PermissionDenied

    collaborator = get_object_or_404(FormCollaborator, form=form_obj, user_id=user_id)

    if request.method == "POST":
        username = collaborator.user.username
        collaborator.delete()
        messages.success(request, _('Collaborator "%(username)s" has been removed.') % {"username": username})
        return redirect("euniforms:collaborators_list", form_pk=form_obj.pk)

    context = {
        "form_obj": form_obj,
        "collaborator": collaborator,
    }
    return render(request, "euniforms/manage/collaborator_confirm_remove.html", context)


# ---------------------------------------------------------------------------
# Responses (manager OR viewer-group access)
# ---------------------------------------------------------------------------


@login_required
def responses_list(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)
    if not form_obj.user_can_view_responses(request.user):
        raise PermissionDenied

    # Get filter parameters
    search_query = request.GET.get("search", "").strip()
    submitter_filter = request.GET.get("submitter", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    fields = list(form_obj.fields.all())
    responses = form_obj.responses.select_related("user").prefetch_related("answers")

    # Apply filters using database queries for better performance
    from django.db.models import Q

    if submitter_filter:
        responses = responses.filter(
            Q(user__username__icontains=submitter_filter) |
            Q(main_character_name__icontains=submitter_filter)
        )

    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            responses = responses.filter(submitted_at__date__gte=date_from_obj)
        except ValueError:
            pass  # Invalid date format, ignore filter

    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            responses = responses.filter(submitted_at__date__lte=date_to_obj)
        except ValueError:
            pass  # Invalid date format, ignore filter

    # Apply content search filter at database level for better performance
    if search_query:
        # Search in FormAnswer values - this uses the database instead of Python
        response_ids_with_matching_answers = FormAnswer.objects.filter(
            response__form=form_obj,
            value__icontains=search_query
        ).values_list('response_id', flat=True).distinct()

        responses = responses.filter(id__in=response_ids_with_matching_answers)

    # Build response rows - prefetch answers to avoid N+1 queries
    responses = responses.prefetch_related('answers__field')

    rows = []
    for response in responses:
        # Create efficient lookup dictionary
        answers_by_field = {a.field_id: a for a in response.answers.all()}

        rows.append(
            {
                "response": response,
                "cells": [answers_by_field.get(field.pk) for field in fields],
            }
        )

    context = {
        "form_obj": form_obj,
        "fields": fields,
        "rows": rows,
        "can_manage": request.user.has_perm("euniforms.manage_forms"),
        "search_query": search_query,
        "submitter_filter": submitter_filter,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "euniforms/manage/responses_list.html", context)


@login_required
def response_detail(request, response_pk):
    response = get_object_or_404(
        FormResponse.objects.select_related("form", "user"), pk=response_pk
    )
    if not response.form.user_can_view_responses(request.user):
        raise PermissionDenied
    return render(
        request,
        "euniforms/manage/response_detail.html",
        {
            "response": response,
            "form_obj": response.form,
            "answers": response.answers.all(),
        },
    )


@login_required
def responses_csv(request, form_pk):
    form_obj = get_object_or_404(Form, pk=form_pk)

    if not form_obj.user_can_view_responses(request.user):
        raise PermissionDenied

    fields = list(form_obj.fields.all())

    http_response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )
    http_response.write("\ufeff")  # UTF-8 BOM for Excel

    filename = f"{slugify(form_obj.title) or 'form'}-responses.csv"
    http_response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    # Use semicolon delimiter for better Excel compatibility in many locales
    writer = csv.writer(http_response, delimiter=";")

    writer.writerow(
        [_("Submitted at"), _("Submitter"), _("Main character")]
        + [field.label for field in fields]
    )

    responses = (
        form_obj.responses
        .select_related("user")
        .prefetch_related("answers")
    )

    for response in responses:
        answers_by_field = {
            answer.field_id: answer
            for answer in response.answers.all()
        }

        row = [
            response.submitted_at.strftime("%Y-%m-%d %H:%M"),
            response.user.username if response.user else "",
            response.main_character_name,
        ]

        for field in fields:
            answer = answers_by_field.get(field.pk)
            row.append(answer.display_value() if answer else "")

        writer.writerow(row)

    return http_response


@login_required
def response_delete(request, response_pk):
    """Delete a form response (does not trigger Discord notifications)."""
    response = get_object_or_404(
        FormResponse.objects.select_related("form", "user"), pk=response_pk
    )

    # Check permissions - only managers or form viewers can delete responses
    if not response.form.user_can_view_responses(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form_obj = response.form
        submitter_name = response.submitter_display

        # Delete the response directly (this will cascade delete answers)
        response.delete()

        # Log the deletion
        app_logger.info(
            f"Response deleted by {request.user.username}",
            event_type="response_deleted",
            form_id=form_obj.pk,
            form_title=form_obj.title,
            response_id=response_pk,
            submitter=submitter_name,
            deleted_by_id=request.user.id,
            deleted_by=request.user.username
        )

        messages.success(
            request,
            _('Response from "%(submitter)s" has been deleted.') % {"submitter": submitter_name}
        )
        return redirect("euniforms:responses_list", form_pk=form_obj.pk)

    return render(
        request,
        "euniforms/manage/response_confirm_delete.html",
        {"response": response, "form_obj": response.form}
    )
