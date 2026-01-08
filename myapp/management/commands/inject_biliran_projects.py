from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import Project
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Inject dummy project data for Biliran only'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of projects to create (default: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing projects before adding new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        if options['clear']:
            Project.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared all existing projects'))

        # Biliran only data
        biliran_municipalities = ['Almeria', 'Biliran', 'Caibiran', 'Culaba', 'Maripipi', 'San Mariano', 'Santo Domingo']
        programs = ['Crop Production', 'Livestock Production', 'Fisheries', 'Post-Harvest', 'Food Processing', 'Renewable Energy']
        fund_sources = ['National Fund', 'Provincial Fund', 'Municipal Fund', 'Special Appropriation', 'Donor Fund']
        project_types = ['Infrastructure', 'Livelihood', 'Technology Transfer', 'Training Program', 'Research']
        statuses = ['Planning', 'On-going', 'Completed', 'Delayed', 'Cancelled']
        
        beneficiaries = [
            'Farmer Cooperative A',
            'Fishermen Association B',
            'Women Farmers Group C',
            'Youth Organization D',
            'Community Association E'
        ]

        base_date = timezone.now()
        created_count = 0

        for i in range(1, count + 1):
            municipality = random.choice(biliran_municipalities)
            
            project_start = base_date - timedelta(days=random.randint(30, 365))
            project_end = project_start + timedelta(days=random.randint(60, 180))
            
            allocated_funds = random.randint(100000, 1000000)
            released_funds = int(allocated_funds * random.uniform(0.5, 1.0))
            liquidated_funds = int(released_funds * random.uniform(0.5, 1.0))
            
            project = Project.objects.create(
                # Identification
                no=i,
                project_code=f'PROJ-{base_date.year:04d}-{i:03d}',
                year=base_date.year,
                status=random.choice(statuses),
                
                # Basic Info
                project_title=f'Development Project {i}: {random.choice(["Irrigation", "Aquaculture", "Crop Diversification", "Livestock Raising", "Fishery Enhancement"])} in {municipality}',
                agency_grantee='Department of Agriculture - Biliran Office',
                program=random.choice(programs),
                type_of_project=random.choice(project_types),
                remarks=f'Test project {i} for Biliran demonstration',
                
                # Location
                mun=municipality,
                province='Biliran',
                district='District ' + str(random.randint(1, 3)),
                
                # Beneficiaries
                beneficiary=random.choice(beneficiaries),
                beneficiary_address=f'{municipality}, Biliran',
                contact_details=f'(055) 123-{4567 + i:04d}',
                proponent_details=f'Proponent Name {i}',
                no_of_beneficiaries=random.randint(10, 100),
                male=random.randint(5, 50),
                female=random.randint(5, 50),
                senior_citizen=random.randint(0, 20),
                pwd=random.randint(0, 10),
                
                # Financials
                fund_source=random.choice(fund_sources),
                funds=allocated_funds,
                total_project_cost=allocated_funds + random.randint(50000, 200000),
                counterpart_funds=random.randint(50000, 500000),
                internally_managed_fund=random.randint(0, 100000),
                total_funds_released=released_funds,
                
                # Tranches
                first_tranche=int(allocated_funds * 0.4),
                second_tranche=int(allocated_funds * 0.3),
                third_tranche=int(allocated_funds * 0.3),
                
                # Liquidation
                check_ada_no=f'ADA-{2024}-{1000+i:04d}',
                status_of_liquidation=random.choice(['Completed', 'Ongoing', 'Pending']),
                date_of_liquidation=project_end + timedelta(days=random.randint(1, 30)) if random.random() > 0.3 else None,
                amount_liquidated=liquidated_funds,
                
                # Dates
                project_start=project_start,
                project_end=project_end,
                date_of_release=project_start + timedelta(days=random.randint(0, 30)),
                date_of_completion=project_end if random.random() > 0.3 else None,
                original_project_duration='6 months',
                extension_date=None,
                
                # Tech/Interventions
                availed_technologies='Improved Seeds, Better Farming Practices, Equipment Support',
                interventions='Training, Equipment provision, Market linkage',
                
                # Checklist/Docs
                tafr=random.choice(['Yes', 'No', 'Pending']),
                par=random.choice(['Yes', 'No', 'Pending']),
                list_of_eqpt=random.choice(['Yes', 'No', 'Pending']),
                terminal_report=random.choice(['Yes', 'No', 'Pending']),
                invoice_receipt=random.choice(['Yes', 'No', 'Pending']),
                donated=random.choice(['Yes', 'No']),
                date_of_donation=project_start + timedelta(days=random.randint(1, 60)) if random.random() > 0.5 else None,
                acknowledgment_receipt_by_grantee=random.choice(['Yes', 'No', 'Pending']),
                
                # Extra
                donation_status=random.choice(['None', 'Received', 'Pending']),
                pme_visit=random.choice(['Yes', 'No']),
                womens_group=random.choice(['Yes', 'No']),
            )
            created_count += 1
            self.stdout.write(f'Created project {i}: {project.project_title}')

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {created_count} dummy projects for Biliran!')
        )
