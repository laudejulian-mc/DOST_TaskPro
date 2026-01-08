"""
Management command to inject dummy Proposal data.
For each existing Project that lacks a linked Proposal, creates a synced Proposal.
Also creates some standalone (unlinked) proposals for testing.
"""
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import Proposal, Project, Budget, User


class Command(BaseCommand):
    help = "Inject dummy proposals synced with existing projects and add standalone proposals."

    def add_arguments(self, parser):
        parser.add_argument(
            '--standalone',
            type=int,
            default=5,
            help='Number of standalone (unlinked) proposals to create (default: 5)'
        )

    def handle(self, *args, **options):
        standalone_count = options['standalone']

        # Get active budgets
        budgets = list(Budget.objects.filter(status='active'))
        if not budgets:
            self.stdout.write(self.style.WARNING("No active budgets found. Creating a default budget."))
            budgets = [Budget.objects.create(
                fiscal_year=2025,
                fund_source='General Fund',
                total_equipment_value=Decimal('10000000.00'),
                delivered_equipment_value=Decimal('0.00'),  # No deliveries yet
                status='active'
            )]

        # Get users for assigning
        users = list(User.objects.all())
        proponents = list(User.objects.filter(role='proponent'))
        beneficiaries = list(User.objects.filter(role='beneficiary'))
        staff = list(User.objects.filter(role='dost_staff'))

        # Fallback if no users exist
        if not users:
            self.stdout.write(self.style.ERROR("No users found. Cannot create proposals."))
            return

        created_synced = 0
        created_standalone = 0

        # 1. Create Proposals for Projects that lack them
        for project in Project.objects.all():
            # Skip if project already has a proposal linked
            if project.proposal_id is not None:
                self.stdout.write(f"  Skipping Project {project.id} (already has proposal_id={project.proposal_id})")
                continue
            
            budget = project.budget or random.choice(budgets)
            submitted_by = random.choice(staff) if staff else random.choice(users)
            processed_by = random.choice(proponents) if proponents else random.choice(users)
            beneficiary = random.choice(beneficiaries) if beneficiaries else None

            proposed_amount = project.funds or Decimal(random.randint(50000, 500000))
            approved_amount = proposed_amount

            # Create proposal with 'pending' status first to avoid signal creating a new project
            proposal = Proposal.objects.create(
                title=project.project_title or f"Proposal for Project {project.id}",
                description=project.project_description or "Auto-generated proposal description.",
                submitted_by=submitted_by,
                status='pending',  # Start as pending
                proposed_amount=proposed_amount,
                approved_amount=approved_amount,
                budget=budget,
                processed_by=processed_by,
                beneficiary=beneficiary,
            )

            # Link the project to this proposal FIRST
            project.proposal = proposal
            project.save(update_fields=['proposal'])
            
            # NOW update the proposal status to approved (the signal will find the existing project)
            proposal.status = 'approved'
            proposal.save(update_fields=['status'])

            created_synced += 1
            self.stdout.write(f"  Created proposal for Project {project.id}: {proposal.title[:40]}")

        # 2. Create standalone proposals (not linked to projects)
        statuses = ['pending', 'for_review', 'approved', 'rejected', 'needs_revision']
        standalone_titles = [
            "Community Solar Panel Installation",
            "Agricultural Equipment Modernization",
            "Fishery Cold Storage Facility",
            "Women's Livelihood Training Program",
            "Youth Tech Skills Development",
            "Mobile Health Clinic Equipment",
            "Seaweed Farming Expansion",
            "Organic Fertilizer Production",
            "Disaster Preparedness Equipment",
            "Eco-Tourism Development Project",
            "Mangrove Reforestation Initiative",
            "Handicraft Export Training",
            "Tilapia Hatchery Establishment",
            "Community Water System Upgrade",
            "Rice Mill Modernization",
        ]

        for i in range(standalone_count):
            budget = random.choice(budgets)
            submitted_by = random.choice(staff) if staff else random.choice(users)
            processed_by = random.choice(proponents) if proponents else random.choice(users)
            beneficiary = random.choice(beneficiaries) if beneficiaries else None
            status = random.choice(statuses)

            proposed_amount = Decimal(random.randint(25000, 750000))
            approved_amount = proposed_amount if status == 'approved' else None

            title = random.choice(standalone_titles) + f" #{random.randint(100, 999)}"
            description = f"This proposal aims to support {title.lower()} for the benefit of the community."

            Proposal.objects.create(
                title=title,
                description=description,
                submitted_by=submitted_by,
                status=status,
                proposed_amount=proposed_amount,
                approved_amount=approved_amount,
                budget=budget,
                processed_by=processed_by,
                beneficiary=beneficiary,
            )

            created_standalone += 1

        self.stdout.write(self.style.SUCCESS(
            f"Injected {created_synced} synced proposals (linked to projects) and {created_standalone} standalone proposals."
        ))
