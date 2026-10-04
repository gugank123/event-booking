from django.db import migrations


def verify_existing(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email_verified=False).update(email_verified=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_email_verified_user_phone_auditlog_and_more")]

    operations = [migrations.RunPython(verify_existing, migrations.RunPython.noop)]
