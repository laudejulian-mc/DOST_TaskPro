from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from django.urls import reverse
from django.utils import timezone
import logging

from .models import Project, Task, Notification, Proposal, Message
from .models import User  # adjust based on your project

logger = logging.getLogger(__name__)


# ------------------------
# Notify proponents + ALL beneficiaries for short projects (≤ 3 months)
# ------------------------
@receiver(post_save, sender=Project)
def notify_short_project(sender, instance, created, **kwargs):

    # Ensure proponent exists
    if not instance.proposal or not instance.proposal.processed_by:
        return

    if instance.start_date and instance.end_date:
        duration_days = (instance.end_date - instance.start_date).days

        if duration_days <= 90:

            # Avoid duplicate notification to proponent
            exists = Notification.objects.filter(
                receiver=instance.proposal.processed_by,
                message__icontains=f"Project '{instance.project_title}' has a short duration"
            ).exists()

            if not exists:
                # -----------------------------
                # ✔ SEND TO PROPONENT
                # -----------------------------
                Notification.objects.create(
                    sender=None,
                    receiver=instance.proposal.processed_by,
                    message=(
                        f"Project '{instance.project_title}' has a short duration ({duration_days} days). "
                        f"Please prepare an extension letter and submit the fund utilization report."
                    ),
                    category='project',
                    link=reverse('proponent_projects_url')
                )

            # -----------------------------
            # ✔ SEND TO ALL BENEFICIARIES
            # -----------------------------
            all_beneficiaries = User.objects.filter(role="beneficiary")

            for b in all_beneficiaries:

                # Avoid duplicates for beneficiaries
                exists_b = Notification.objects.filter(
                    receiver=b,
                    message__icontains=f"Project '{instance.project_title}' is short in duration"
                ).exists()

                if not exists_b:
                    Notification.objects.create(
                        sender=None,
                        receiver=b,
                        message=(
                            f"Project '{instance.project_title}' is short in duration ({duration_days} days). "
                            f"Please coordinate with the proponent regarding the extension letter and fund utilization."
                        ),
                        category='project',
                        link=reverse('beneficiary_projects_url')
                    )



# ------------------------
# Notify proponents for overdue tasks
# ------------------------
@receiver(post_save, sender=Task)
def notify_overdue_task(sender, instance, created, **kwargs):

    if not instance.project or not instance.project.proposal or not instance.project.proposal.processed_by:
        return

    proponent = instance.project.proposal.processed_by
    today = date.today()

    # Ensure due_date exists and is date type
    if isinstance(instance.due_date, str):
        from datetime import datetime
        instance.due_date = datetime.strptime(instance.due_date, "%Y-%m-%d").date()

    # Add the field dynamically if missing
    if not hasattr(instance, 'due_date_notified'):
        instance.due_date_notified = False

    # Notify if overdue and not yet notified
    if instance.due_date and instance.due_date <= today and not instance.due_date_notified:
        Notification.objects.create(
            sender=None,
            receiver=proponent,
            message=(
                f"Task '{instance.title}' is overdue (was due {instance.due_date}). "
                f"Please take necessary action, prepare an extension letter if needed, "
                f"and submit required reports."
            ),
            category='task',
            link=reverse('proponent_task_list_url')
        )

        instance.due_date_notified = True
        instance.save(update_fields=['due_date_notified'])


# ------------------------
# Notify users when they receive new messages
# ------------------------
@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created and instance.message_type == 'direct':
        # Determine the appropriate conversation URL based on recipient's role
        role_url_mapping = {
            'admin': 'administrator_conversation_url',
            'dost_staff': 'staff_conversation_url',
            'proponent': 'proponent_conversation_url',
            'beneficiary': 'beneficiary_conversation_url',
        }

        conversation_url_name = role_url_mapping.get(instance.recipient.role, 'staff_conversation_url')

        # Create notification for the recipient
        subject_text = f": {instance.subject}" if instance.subject else ""
        Notification.objects.create(
            sender=instance.sender,
            receiver=instance.recipient,
            message=f"New message from {instance.sender.get_full_name()}{subject_text}",
            link=reverse(conversation_url_name, kwargs={'partner_id': instance.sender.id})
        )