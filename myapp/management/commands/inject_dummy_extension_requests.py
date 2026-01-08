"""
Management command to inject dummy Extension Request data.
Uses existing proponents and proposals from the database.
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from myapp.models import ExtensionRequest, Proposal, User


class Command(BaseCommand):
    help = "Inject dummy extension requests using existing proponents and proposals."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of extension requests to create (default: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing extension requests before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            deleted_count = ExtensionRequest.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Cleared {deleted_count} existing extension requests."))

        # Get existing proponents
        proponents = list(User.objects.filter(role='proponent'))
        if not proponents:
            self.stdout.write(self.style.ERROR("No proponents found. Cannot create extension requests."))
            return

        # Get existing proposals (preferably those with proponents assigned)
        proposals = list(Proposal.objects.filter(proponent__isnull=False).select_related('proponent', 'project'))
        if not proposals:
            # Fallback to all proposals
            proposals = list(Proposal.objects.all().select_related('proponent', 'project'))
        
        if not proposals:
            self.stdout.write(self.style.ERROR("No proposals found. Cannot create extension requests."))
            return

        # Get admin users for approving some requests
        admins = list(User.objects.filter(role='admin'))

        # Reasons for extension requests
        reasons = [
            "Due to unforeseen weather conditions, we need additional time to complete the project deliverables.",
            "Supply chain delays have affected the delivery of essential equipment and materials.",
            "Technical challenges encountered during implementation require additional time for resolution.",
            "Community consultation process took longer than expected due to scheduling conflicts.",
            "Additional training sessions were required for beneficiaries to ensure proper equipment usage.",
            "Coordination with local government units required more time than initially planned.",
            "The project scope was expanded based on community feedback and needs assessment.",
            "Health and safety protocols implementation required additional preparation time.",
            "Procurement processes experienced delays due to documentation requirements.",
            "Natural disaster recovery efforts in the area affected project timeline.",
            "Key personnel changes necessitated transition period and knowledge transfer.",
            "Quality assurance testing revealed issues that required additional time to address.",
            "Stakeholder approval processes took longer than anticipated.",
            "Budget reallocation requests required additional administrative processing time.",
            "Seasonal factors affecting agricultural activities required schedule adjustments.",
        ]

        # Remarks for approved/rejected requests
        approval_remarks = [
            "Extension approved. Please submit progress report within 30 days.",
            "Request granted. Ensure deliverables are completed within the extended timeline.",
            "Approved with the condition that weekly status updates are provided.",
            "Extension approved. Final inspection will be scheduled after the new deadline.",
        ]

        rejection_remarks = [
            "Request denied. Project has already exceeded maximum allowable extensions.",
            "Insufficient justification provided for the extension request.",
            "Request rejected. Alternative solutions should be explored to meet original deadline.",
            "Extension denied. Please coordinate with project management for assistance.",
        ]

        created_count = 0
        statuses = ['pending', 'approved', 'rejected']
        status_weights = [0.5, 0.35, 0.15]  # 50% pending, 35% approved, 15% rejected

        for i in range(count):
            proposal = random.choice(proposals)
            
            # Use the proposal's proponent if available, otherwise pick random proponent
            if proposal.proponent:
                proponent = proposal.proponent
            else:
                proponent = random.choice(proponents)

            status = random.choices(statuses, weights=status_weights)[0]
            requested_days = random.randint(7, 60)
            
            # Create base extension request
            extension_request = ExtensionRequest(
                proposal=proposal,
                proponent=proponent,
                reason=random.choice(reasons),
                requested_extension_days=requested_days,
                status=status,
            )

            # Set dates - spread over the last 6 months
            days_ago = random.randint(1, 180)
            extension_request.date_submitted = timezone.now() - timedelta(days=days_ago)

            # Handle approved/rejected status
            if status == 'approved':
                extension_request.approved_days = random.randint(max(7, requested_days - 14), requested_days + 7)
                extension_request.remarks = random.choice(approval_remarks)
                if admins:
                    extension_request.approved_by = random.choice(admins)
                extension_request.date_approved = extension_request.date_submitted + timedelta(days=random.randint(1, 14))
            elif status == 'rejected':
                extension_request.remarks = random.choice(rejection_remarks)
                if admins:
                    extension_request.approved_by = random.choice(admins)
                extension_request.date_approved = extension_request.date_submitted + timedelta(days=random.randint(1, 14))

            extension_request.save()
            created_count += 1

            status_display = status.upper()
            self.stdout.write(
                f"  Created [{status_display}] extension request for '{proposal.title[:40]}...' "
                f"by {proponent.full_name()} - {requested_days} days requested"
            )

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created {created_count} extension requests."))
        
        # Summary
        pending = ExtensionRequest.objects.filter(status='pending').count()
        approved = ExtensionRequest.objects.filter(status='approved').count()
        rejected = ExtensionRequest.objects.filter(status='rejected').count()
        
        self.stdout.write(f"\nExtension Request Summary:")
        self.stdout.write(f"  Pending:  {pending}")
        self.stdout.write(f"  Approved: {approved}")
        self.stdout.write(f"  Rejected: {rejected}")
        self.stdout.write(f"  Total:    {pending + approved + rejected}")
