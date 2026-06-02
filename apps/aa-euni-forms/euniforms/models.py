"""Data models for the EVE Uni Forms app."""

# Django
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re


class General(models.Model):
    """Meta-model that only carries the app's permissions (no table of its own)."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access the Forms app and fill out eligible forms"),
            (
                "manage_forms",
                "Can create, edit and delete forms and view all responses",
            ),
        )


class GroupStateMapping(models.Model):
    """Maps groups to user states for form restrictions."""

    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='state_mapping'
    )
    state = models.CharField(max_length=50)

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        return f"{self.group.name} → {self.state}"


class Form(models.Model):
    """A form / survey that members can fill out."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        OPEN = "OPEN", _("Open")
        CLOSED = "CLOSED", _("Closed")

    title = models.CharField(max_length=254)
    description = models.TextField(
        blank=True, help_text=_("Shown to people before they fill out the form.")
    )
    introduction_text = models.TextField(
        blank=True,
        help_text=_("Additional text shown at the top of the question sheet when filling out the form.")
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    restricted_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="+",
        help_text=_(
            "Only members of these groups may fill out the form. "
            "Leave empty to allow any logged-in user."
        ),
    )
    viewer_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="+",
        help_text=_("Members of these groups may read the responses to this form."),
    )

    # State-based restrictions
    restricted_states = models.JSONField(
        default=list,
        blank=True,
        help_text=_(
            "User states that may fill out the form. "
            "Leave empty to allow any state. Common states: member, student, alumni, inactive"
        ),
    )
    restrict_by_group = models.BooleanField(
        default=True,
        help_text=_("Enable group-based restrictions")
    )
    restrict_by_state = models.BooleanField(
        default=False,
        help_text=_("Enable state-based restrictions")
    )
    restriction_logic = models.CharField(
        max_length=3,
        choices=[
            ('OR', _('Either group OR state (less restrictive)')),
            ('AND', _('Both group AND state (more restrictive)'))
        ],
        default='OR',
        help_text=_("How to combine group and state restrictions when both are enabled")
    )

    allow_multiple = models.BooleanField(
        default=False,
        help_text=_("Allow a person to submit this form more than once."),
    )
    notify_on_submit = models.BooleanField(
        default=True,
        help_text=_("Send an Auth notification to viewers when a response is submitted."),
    )
    discord_webhook_url = models.URLField(
        blank=True,
        null=True,
        max_length=500,
        help_text=_("Optional Discord webhook URL to send form responses to. Format: https://discord.com/api/webhooks/{id}/{token}"),
    )

    class Meta:
        ordering = ["-created_at"]
        default_permissions = ()
        indexes = [
            models.Index(fields=['status'], name='form_status_idx'),
            models.Index(fields=['created_at'], name='form_created_at_idx'),
            models.Index(fields=['status', 'created_at'], name='form_status_created_idx'),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        """Validate the form fields."""
        super().clean()
        if self.discord_webhook_url:
            self._validate_discord_webhook_url()

    def _validate_discord_webhook_url(self):
        """Validate that the Discord webhook URL has the correct format."""
        if not self.discord_webhook_url:
            return

        # Discord webhook URL pattern: https://discord.com/api/webhooks/{id}/{token}
        pattern = r'^https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+$'
        if not re.match(pattern, self.discord_webhook_url):
            raise ValidationError({
                'discord_webhook_url': _(
                    'Invalid Discord webhook URL format. Expected: '
                    'https://discord.com/api/webhooks/{id}/{token}'
                )
            })

    @property
    def accepts_submissions(self) -> bool:
        """Whether the form is currently accepting responses."""
        return self.status == self.Status.OPEN

    def is_eligible(self, user) -> bool:
        """Whether ``user`` is allowed to fill this form (ignoring status).

        Managers may always fill (so they can preview). Otherwise, the user must
        meet the configured group and/or state restrictions based on the form's settings.
        """
        if not user.is_authenticated:
            return False
        if user.has_perm("euniforms.manage_forms"):
            return True

        group_eligible = self._check_group_eligibility(user)
        state_eligible = self._check_state_eligibility(user)

        if self.restrict_by_group and self.restrict_by_state:
            # Both restrictions are active
            if self.restriction_logic == 'AND':
                return group_eligible and state_eligible
            else:  # OR logic
                return group_eligible or state_eligible
        elif self.restrict_by_group:
            return group_eligible
        elif self.restrict_by_state:
            return state_eligible
        else:
            # No restrictions enabled - allow any authenticated user
            return True

    def _check_group_eligibility(self, user) -> bool:
        """Check if user meets group requirements."""
        if not self.restricted_groups.exists():
            return True
        return self.restricted_groups.filter(
            pk__in=user.groups.values_list("pk", flat=True)
        ).exists()

    def _check_state_eligibility(self, user) -> bool:
        """Check if user meets state requirements."""
        if not self.restricted_states:
            return True

        user_state = self._get_user_state(user)
        if not user_state:
            return False

        return user_state in self.restricted_states

    def _get_user_state(self, user) -> str:
        """Get user's current state based on configured group-to-state mappings."""
        user_groups = list(user.groups.all())
        if not user_groups:
            return 'member' if user.is_active else 'inactive'

        # Check if any of the user's groups have configured state mappings
        for group in user_groups:
            try:
                mapping = GroupStateMapping.objects.get(group=group)
                return mapping.state
            except GroupStateMapping.DoesNotExist:
                continue

        # No mapping found - return default state
        return 'member' if user.is_active else 'inactive'

    @classmethod
    def get_available_states(cls):
        """Get all available states from configured group mappings."""
        # Get all unique states from GroupStateMapping
        states = list(GroupStateMapping.objects.values_list('state', flat=True).distinct())

        # Always include basic default states
        basic_states = ['member', 'inactive']
        for state in basic_states:
            if state not in states:
                states.append(state)

        return sorted(states)

    @classmethod
    def get_state_choices(cls):
        """Get state choices formatted for Django form fields."""
        states = cls.get_available_states()
        return [(state, state.title()) for state in states]

    def user_can_view_responses(self, user) -> bool:
        """Whether ``user`` may read this form's responses."""
        if not user.is_authenticated:
            return False
        if user.has_perm("euniforms.manage_forms"):
            return True
        return self.viewer_groups.filter(
            pk__in=user.groups.values_list("pk", flat=True)
        ).exists()

    def has_response_from(self, user) -> bool:
        """Whether ``user`` has already submitted a response to this form."""
        if not user.is_authenticated:
            return False
        return self.responses.filter(user=user).exists()

    def notification_recipients(self):
        """Users who should be notified when a response is submitted."""
        recipients = User.objects.filter(groups__in=self.viewer_groups.all())
        if self.created_by_id:
            recipients = recipients | User.objects.filter(pk=self.created_by_id)
        return recipients.distinct()


class FormField(models.Model):
    """A single question on a :class:`Form`."""

    class FieldType(models.TextChoices):
        SHORT_TEXT = "SHORT_TEXT", _("Short text")
        LONG_TEXT = "LONG_TEXT", _("Paragraph text")
        FREE_TEXT = "FREE_TEXT", _("Free text (up to 1000 characters)")
        SINGLE_CHOICE = "SINGLE_CHOICE", _("Single choice")
        MULTI_CHOICE = "MULTI_CHOICE", _("Multiple choice")
        NUMBER = "NUMBER", _("Number")
        DATE = "DATE", _("Date")
        BOOLEAN = "BOOLEAN", _("Yes / No")
        EVE_CHARACTER = "EVE_CHARACTER", _("EVE character (verified)")

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="fields")
    order = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=254)
    help_text = models.CharField(max_length=254, blank=True)
    field_type = models.CharField(
        max_length=20, choices=FieldType.choices, default=FieldType.SHORT_TEXT
    )
    required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "pk"]
        default_permissions = ()

    def __str__(self) -> str:
        return self.label

    @property
    def is_choice_type(self) -> bool:
        return self.field_type in (
            self.FieldType.SINGLE_CHOICE,
            self.FieldType.MULTI_CHOICE,
        )


class FieldChoice(models.Model):
    """A selectable option for a choice-type :class:`FormField`."""

    field = models.ForeignKey(
        FormField, on_delete=models.CASCADE, related_name="choices"
    )
    order = models.PositiveIntegerField(default=0)
    value = models.CharField(max_length=254)

    class Meta:
        ordering = ["order", "pk"]
        default_permissions = ()

    def __str__(self) -> str:
        return self.value


class FormResponse(models.Model):
    """One submission of a :class:`Form` by a user.

    The submitting user and their main character are snapshotted so the
    attribution survives the user changing their main or being deleted.
    """

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    main_character_id = models.PositiveBigIntegerField(null=True, blank=True)
    main_character_name = models.CharField(max_length=254, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        default_permissions = ()
        indexes = [
            models.Index(fields=['submitted_at'], name='response_submitted_at_idx'),
            models.Index(fields=['form', 'submitted_at'], name='response_form_submitted_idx'),
            models.Index(fields=['user'], name='response_user_idx'),
            models.Index(fields=['main_character_name'], name='response_character_name_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.form.title} — {self.submitter_display}"

    @property
    def submitter_display(self) -> str:
        if self.main_character_name:
            return self.main_character_name
        if self.user:
            return self.user.username
        return str(_("Unknown"))


class FormAnswer(models.Model):
    """An answer to a single :class:`FormField` within a :class:`FormResponse`.

    The value is stored as JSON so every field type round-trips with full
    fidelity (lists for multi-choice, an ``{id, name}`` object for the verified
    character picker, etc.). ``field_label``/``field_type`` are snapshotted so a
    later edit or deletion of the question doesn't corrupt historical answers.
    """

    response = models.ForeignKey(
        FormResponse, on_delete=models.CASCADE, related_name="answers"
    )
    field = models.ForeignKey(
        FormField, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    field_label = models.CharField(max_length=254)
    field_type = models.CharField(max_length=20)
    value = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]
        default_permissions = ()
        indexes = [
            models.Index(fields=['response'], name='answer_response_idx'),
            models.Index(fields=['field'], name='answer_field_idx'),
            models.Index(fields=['response', 'field'], name='answer_response_field_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.field_label}: {self.display_value()}"

    def display_value(self) -> str:
        """A human-readable rendering of the answer, used by templates and CSV."""
        value = self.value
        if value is None or value == "":
            return ""
        if self.field_type == FormField.FieldType.BOOLEAN:
            return str(_("Yes")) if value else str(_("No"))
        if self.field_type == FormField.FieldType.MULTI_CHOICE:
            if isinstance(value, (list, tuple)):
                return ", ".join(str(item) for item in value)
            return str(value)
        if self.field_type == FormField.FieldType.EVE_CHARACTER:
            if isinstance(value, dict):
                return value.get("character_name", "")
            return str(value)
        return str(value)
