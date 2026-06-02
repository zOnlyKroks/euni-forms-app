"""Django admin registration (for superusers; Directors use the in-app UI)."""

# Django
from django.contrib import admin

# AA EVE Uni Forms
from euniforms.models import FieldChoice, Form, FormAnswer, FormField, FormResponse, GroupStateMapping


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)
    filter_horizontal = ("restricted_groups", "viewer_groups")
    inlines = [FormFieldInline]


class FieldChoiceInline(admin.TabularInline):
    model = FieldChoice
    extra = 0


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ("label", "form", "field_type", "order", "required")
    list_filter = ("field_type",)
    search_fields = ("label",)
    inlines = [FieldChoiceInline]


class FormAnswerInline(admin.TabularInline):
    model = FormAnswer
    extra = 0
    readonly_fields = ("field", "field_label", "field_type", "value")
    can_delete = False


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ("form", "submitter_display", "submitted_at")
    list_filter = ("form",)
    date_hierarchy = "submitted_at"
    inlines = [FormAnswerInline]


@admin.register(GroupStateMapping)
class GroupStateMappingAdmin(admin.ModelAdmin):
    list_display = ("group", "state")
    list_filter = ("state",)
    search_fields = ("group__name", "state")
    ordering = ("state", "group__name")
