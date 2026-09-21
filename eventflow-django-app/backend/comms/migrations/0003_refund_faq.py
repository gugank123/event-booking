from django.db import migrations


def add_refund_faq(apps, schema_editor):
    FAQ = apps.get_model("comms", "FAQ")
    FAQ.objects.get_or_create(
        category="Refunds",
        question="How do refunds work?",
        defaults={
            "answer": "Cancelling a booking from My tickets releases your tickets immediately. Because checkout is simulated, no real charge exists — nothing further is taken and you receive a cancellation email for your records.",
            "order": 1,
            "is_published": True,
        },
    )


def remove_refund_faq(apps, schema_editor):
    FAQ = apps.get_model("comms", "FAQ")
    FAQ.objects.filter(category="Refunds", question="How do refunds work?").delete()


class Migration(migrations.Migration):
    dependencies = [("comms", "0002_seed_faqs")]

    operations = [migrations.RunPython(add_refund_faq, remove_refund_faq)]
