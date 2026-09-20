from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ATTENDEE = "attendee", "Attendee"
        ORGANIZER = "organizer", "Organizer"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ATTENDEE)
    email = models.EmailField(unique=True)
    # Suspension re-uses Django's built-in is_active flag: a suspended user
    # simply cannot authenticate, which Django already enforces everywhere.
    #
    # Login is by email. We keep AbstractUser's `username` field (so we don't
    # need a custom UserManager) but always set it equal to the email at
    # registration time, and authenticate against that.

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
