from django.db import migrations

FAQS = [
    ("Booking", "How do I book a ticket?", "Open an event, pick a ticket type and quantity, continue to checkout, and pay with any card-shaped number (payments are simulated). Your reference appears instantly and lands in My tickets.", 1),
    ("Booking", "Where can I see my ticket?", "All tickets live under My tickets. Each confirmed booking shows a QR code — tap Show QR at the door.", 2),
    ("Tickets", "How do I select a seat?", "Events sell ticket types (for example General or VIP) rather than numbered seats. Choose a type and quantity; availability is shown live per type.", 3),
    ("Cancellation", "How do I cancel my booking?", "Go to My tickets and press Cancel on a confirmed booking. Cancelled bookings free their tickets immediately and you get an email confirmation.", 4),
    ("Cancellation", "What happens if an event is cancelled?", "Every confirmed attendee gets an in-app notification and an email. Your booking stays visible under My tickets marked cancelled.", 5),
    ("Payments", "Which payments do you accept?", "Checkout is currently simulated: any 12-19 digit card number with a valid MM/YY expiry and CVC works. No real money moves.", 6),
    ("Payments", "Where is my receipt?", "Your booking confirmation email lists the total charged and the card's last four digits.", 7),
    ("Account", "How do I sign in with Google?", "Press Continue with Google on the login or register page. First-time Google users can pick the attendee or organizer role.", 8),
    ("Events", "How do I save events for later?", "Tap the heart on any event card or event page. Everything you save appears under Wishlist.", 9),
    ("Events", "How do I contact the organizer?", "Every event page has a Contact Organizer button. Your message opens a conversation that includes the event automatically.", 10),
    ("Organizer issues", "An organizer isn't responding. What now?", "Open a support ticket from the Help Center with the event name and booking reference, and our team will step in.", 11),
    ("Technical problems", "The site isn't working. What should I try?", "Refresh, sign out and back in, and try another browser. If it persists, file a report from the Help Center describing what happened.", 12),
]


def seed_faqs(apps, schema_editor):
    FAQ = apps.get_model("comms", "FAQ")
    for category, question, answer, order in FAQS:
        FAQ.objects.get_or_create(
            category=category, question=question,
            defaults={"answer": answer, "order": order, "is_published": True},
        )


def unseed_faqs(apps, schema_editor):
    FAQ = apps.get_model("comms", "FAQ")
    FAQ.objects.filter(question__in=[q for _, q, _, _ in FAQS]).delete()


class Migration(migrations.Migration):
    dependencies = [("comms", "0001_initial")]

    operations = [migrations.RunPython(seed_faqs, unseed_faqs)]
