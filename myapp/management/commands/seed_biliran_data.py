"""
Management command to clear all dummy data and inject fresh Biliran-focused sample data.
Run with: python manage.py seed_biliran_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

from myapp.models import (
    User, Budget, Proposal, Project, Task, 
    BudgetTransaction, Notification, AuditLog, ApprovalLog, ProjectExpense
)


class Command(BaseCommand):
    help = 'Clear all data and seed fresh Biliran-focused sample data'

    # Biliran Municipalities with their coordinates
    MUNICIPALITIES = {
        'Almeria': {'lat': 11.6167, 'lng': 124.4333, 'barangays': ['Poblacion', 'Caucab', 'Tabunan', 'Pili', 'Imelda']},
        'Biliran': {'lat': 11.5833, 'lng': 124.4667, 'barangays': ['Poblacion', 'Busali', 'Hugpa', 'Caraycaray', 'Cabungaan']},
        'Cabucgayan': {'lat': 11.4667, 'lng': 124.5500, 'barangays': ['Poblacion', 'Looc', 'Lanawan', 'Manlabang', 'Canila']},
        'Caibiran': {'lat': 11.5500, 'lng': 124.5833, 'barangays': ['Poblacion', 'Victory', 'Palanay', 'Cabibihan', 'Maurang']},
        'Culaba': {'lat': 11.6500, 'lng': 124.5500, 'barangays': ['Poblacion', 'Virginia', 'Acaban', 'Salvacion', 'Marvel']},
        'Kawayan': {'lat': 11.6667, 'lng': 124.5000, 'barangays': ['Poblacion', 'Tucdao', 'Uson', 'Inasuyan', 'Balaquid']},
        'Maripipi': {'lat': 11.7833, 'lng': 124.3333, 'barangays': ['Poblacion', 'Binalayan', 'Casibang', 'Ermita', 'Agutay']},
        'Naval': {'lat': 11.5667, 'lng': 124.4000, 'barangays': ['Poblacion', 'Atipolo', 'Caray-Caray', 'Larrazabal', 'Sto. Niño']},
    }

    # Project types/programs
    PROGRAMS = ['SETUP', 'GIA', 'CEST', 'STARBOOKS', 'TAPI']
    
    # Technology types
    TECHNOLOGIES = [
        'Food Processing Equipment',
        'Agricultural Machinery',
        'Fishing Equipment',
        'Solar Dryer',
        'Rice Mill',
        'Coco Processing',
        'Seaweed Farming',
        'Aquaculture Technology',
        'Handicraft Tools',
        'ICT Equipment'
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Clearing existing data...'))
        
        # Clear existing data (order matters due to foreign keys)
        Notification.objects.all().delete()
        AuditLog.objects.all().delete()
        ApprovalLog.objects.all().delete()
        ProjectExpense.objects.all().delete()
        Task.objects.all().delete()
        BudgetTransaction.objects.all().delete()
        Project.objects.all().delete()
        Proposal.objects.all().delete()
        Budget.objects.all().delete()
        # Keep admin user, delete others
        User.objects.exclude(is_superuser=True).exclude(username='admin').delete()
        
        self.stdout.write(self.style.SUCCESS('Data cleared!'))
        
        # Create users
        self.stdout.write('Creating users...')
        users = self.create_users()
        
        # Create budgets
        self.stdout.write('Creating budgets...')
        budgets = self.create_budgets(users['admin'])
        
        # Create proposals
        self.stdout.write('Creating proposals...')
        proposals = self.create_proposals(users, budgets)
        
        # Create projects
        self.stdout.write('Creating projects...')
        projects = self.create_projects(users, budgets)
        
        # Create tasks
        self.stdout.write('Creating tasks...')
        self.create_tasks(projects, users)
        
        self.stdout.write(self.style.SUCCESS(f'''
============================================
Data seeding complete!
============================================
Users created: {len(users['proponents']) + len(users['beneficiaries']) + len(users['staff'])}
Budgets created: {len(budgets)}
Proposals created: {len(proposals)}
Projects created: {len(projects)}
============================================
        '''))

    def create_users(self):
        """Create sample users for each role"""
        users = {'proponents': [], 'beneficiaries': [], 'staff': [], 'admin': None}
        
        # Get or create admin
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@dost-biliran.gov.ph',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if not admin.has_usable_password():
            admin.set_password('admin123')
            admin.save()
        users['admin'] = admin

        # Proponents (organization heads, cooperative leaders)
        proponent_data = [
            ('jdelacruz', 'Juan', 'D.', 'Dela Cruz', 'Naval', 'naval_fisherfolk_coop@email.com'),
            ('mreyes', 'Maria', 'S.', 'Reyes', 'Almeria', 'almeria_farmers_assoc@email.com'),
            ('rsantos', 'Roberto', 'L.', 'Santos', 'Caibiran', 'caibiran_womens_group@email.com'),
            ('agarcia', 'Ana', 'M.', 'Garcia', 'Biliran', 'biliran_weavers_coop@email.com'),
            ('pcruz', 'Pedro', 'A.', 'Cruz', 'Culaba', 'culaba_seaweed_farmers@email.com'),
        ]
        for uname, fname, mname, lname, mun, email in proponent_data:
            user = User.objects.create_user(
                username=uname,
                password='password123',
                email=email,
                first_name=fname,
                middle_name=mname,
                last_name=lname,
                role='proponent',
                address=f'{mun}, Biliran',
                contact_number=f'0917{random.randint(1000000, 9999999)}'
            )
            users['proponents'].append(user)

        # Beneficiaries
        beneficiary_data = [
            ('beneficiary1', 'Elena', 'R.', 'Magno', 'Kawayan'),
            ('beneficiary2', 'Carlos', 'T.', 'Lumaban', 'Maripipi'),
            ('beneficiary3', 'Rosa', 'P.', 'Abutin', 'Cabucgayan'),
            ('beneficiary4', 'Jose', 'B.', 'Tacloban', 'Naval'),
            ('beneficiary5', 'Luz', 'C.', 'Biliran', 'Almeria'),
            ('beneficiary6', 'Miguel', 'F.', 'Caibiran', 'Caibiran'),
        ]
        for uname, fname, mname, lname, mun in beneficiary_data:
            user = User.objects.create_user(
                username=uname,
                password='password123',
                email=f'{uname}@email.com',
                first_name=fname,
                middle_name=mname,
                last_name=lname,
                role='beneficiary',
                address=f'{mun}, Biliran',
                contact_number=f'0918{random.randint(1000000, 9999999)}'
            )
            users['beneficiaries'].append(user)

        # DOST Staff
        staff_data = [
            ('staff_techno', 'Mark', 'J.', 'Villanueva', 'Technology Transfer Officer'),
            ('staff_srs', 'Grace', 'L.', 'Fernandez', 'Science Research Specialist'),
            ('staff_admin', 'Rey', 'D.', 'Alonzo', 'Administrative Officer'),
        ]
        for uname, fname, mname, lname, position in staff_data:
            user = User.objects.create_user(
                username=uname,
                password='password123',
                email=f'{uname}@dost-biliran.gov.ph',
                first_name=fname,
                middle_name=mname,
                last_name=lname,
                role='dost_staff',
                address='Naval, Biliran',
                contact_number=f'0919{random.randint(1000000, 9999999)}'
            )
            users['staff'].append(user)

        return users

    def create_budgets(self, admin):
        """Create sample budgets"""
        budgets = []
        budget_data = [
            (2024, 'DOST Central Office - SETUP', Decimal('5000000.00')),
            (2024, 'DOST Region VIII - GIA', Decimal('3000000.00')),
            (2025, 'DOST Central Office - SETUP', Decimal('6000000.00')),
            (2025, 'DOST Region VIII - GIA', Decimal('4000000.00')),
            (2025, 'Provincial S&T Fund', Decimal('2000000.00')),
        ]
        for year, source, amount in budget_data:
            budget = Budget.objects.create(
                fiscal_year=year,
                fund_source=source,
                total_equipment_value=amount,
                delivered_equipment_value=amount * Decimal('0.4'),  # 40% delivered (60% remaining)
                date_allocated=timezone.now().date().replace(month=1, day=15),
                status='active',
                created_by=admin
            )
            budgets.append(budget)
        return budgets

    def create_proposals(self, users, budgets):
        """Create sample proposals across municipalities"""
        proposals = []
        
        proposal_data = [
            # Pending proposals
            ('Community-Based Seaweed Farming in Maripipi', 'pending', 'Maripipi', 250000),
            ('Solar Dryer for Cassava Processing - Kawayan', 'pending', 'Kawayan', 180000),
            
            # For review
            ('Fish Processing Center for Culaba Fisherfolk', 'for_review', 'Culaba', 450000),
            ('Handicraft Training Center - Biliran Town', 'for_review', 'Biliran', 320000),
            
            # Approved (these can become projects)
            ('Rice Mill Equipment for Almeria Farmers', 'approved', 'Almeria', 500000),
            ('Coco Sugar Processing Facility - Caibiran', 'approved', 'Caibiran', 380000),
            ('Aquaculture Technology Transfer - Naval', 'approved', 'Naval', 600000),
            
            # Rejected
            ('Duplicate Seaweed Project - Maripipi', 'rejected', 'Maripipi', 200000),
            
            # Needs revision
            ('Incomplete Proposal - Cabucgayan Farmers', 'needs_revision', 'Cabucgayan', 150000),
        ]
        
        for title, status, mun, amount in proposal_data:
            proponent = random.choice(users['proponents'])
            beneficiary_names = ', '.join([u.full_name() for u in random.sample(users['beneficiaries'], min(3, len(users['beneficiaries'])))])
            
            proposal = Proposal.objects.create(
                title=title,
                description=f'This proposal aims to provide {random.choice(self.TECHNOLOGIES).lower()} support to the community in {mun}, Biliran. The project will benefit local farmers, fisherfolk, and their families.',
                submitted_by=proponent,
                status=status,
                proposed_amount=Decimal(str(amount)),
                approved_amount=Decimal(str(amount)) if status == 'approved' else None,
                budget=random.choice(budgets) if status == 'approved' else None,
                proponent=proponent,
                beneficiaries=beneficiary_names,
                location=f'{random.choice(self.MUNICIPALITIES[mun]["barangays"])}, {mun}',
                municipality=mun,
                province='Biliran',
                review_remarks='Under evaluation' if status == 'for_review' else None
            )
            proposals.append(proposal)
        
        return proposals

    def create_projects(self, users, budgets):
        """Create sample projects spread across all municipalities"""
        projects = []
        
        # Generate projects for each municipality
        project_templates = [
            # Naval (Provincial Capital - more projects)
            ('SETUP Food Processing Center - Naval', 'Naval', 'Ongoing', 'SETUP', 800000, 'Food Processing Equipment'),
            ('Community e-Library (STARBOOKS) - Naval', 'Naval', 'Completed', 'STARBOOKS', 250000, 'ICT Equipment'),
            ('Abaca Fiber Processing - Naval', 'Naval', 'Ongoing', 'GIA', 450000, 'Agricultural Machinery'),
            
            # Almeria
            ('Rice Mill Modernization - Almeria', 'Almeria', 'Ongoing', 'SETUP', 550000, 'Rice Mill'),
            ('Organic Vegetable Production - Almeria', 'Almeria', 'Completed', 'GIA', 280000, 'Agricultural Machinery'),
            
            # Biliran Town
            ('Bamboo Craft Production Center - Biliran', 'Biliran', 'Ongoing', 'SETUP', 420000, 'Handicraft Tools'),
            ('STARBOOKS Installation - Biliran NHS', 'Biliran', 'Completed', 'STARBOOKS', 150000, 'ICT Equipment'),
            
            # Cabucgayan
            ('Root Crops Processing - Cabucgayan', 'Cabucgayan', 'New', 'GIA', 380000, 'Food Processing Equipment'),
            ('Coco Coir Production - Cabucgayan', 'Cabucgayan', 'Ongoing', 'CEST', 320000, 'Coco Processing'),
            
            # Caibiran
            ('Muscovado Sugar Mill - Caibiran', 'Caibiran', 'Completed', 'SETUP', 750000, 'Food Processing Equipment'),
            ('Solar Dryer Facility - Caibiran', 'Caibiran', 'Ongoing', 'GIA', 280000, 'Solar Dryer'),
            
            # Culaba
            ('Seaweed Processing Center - Culaba', 'Culaba', 'Ongoing', 'SETUP', 520000, 'Seaweed Farming'),
            ('Fish Drying Facility - Culaba', 'Culaba', 'New', 'GIA', 350000, 'Food Processing Equipment'),
            
            # Kawayan
            ('Cassava Chips Production - Kawayan', 'Kawayan', 'Ongoing', 'CEST', 280000, 'Food Processing Equipment'),
            ('STARBOOKS - Kawayan Central School', 'Kawayan', 'Completed', 'STARBOOKS', 150000, 'ICT Equipment'),
            
            # Maripipi (Island municipality)
            ('Island Fish Processing - Maripipi', 'Maripipi', 'Ongoing', 'SETUP', 480000, 'Fishing Equipment'),
            ('Solar-Powered Ice Plant - Maripipi', 'Maripipi', 'New', 'GIA', 650000, 'Aquaculture Technology'),
        ]
        
        for title, mun, status, program, funds, tech in project_templates:
            coords = self.MUNICIPALITIES[mun]
            barangay = random.choice(coords['barangays'])
            proponent = random.choice(users['proponents'])
            beneficiary = random.choice(users['beneficiaries'])
            
            # Randomize dates based on status
            if status == 'Completed':
                start = timezone.now() - timedelta(days=random.randint(365, 730))
                end = start + timedelta(days=random.randint(180, 365))
                completion = end
            elif status == 'Ongoing':
                start = timezone.now() - timedelta(days=random.randint(30, 180))
                end = timezone.now() + timedelta(days=random.randint(90, 365))
                completion = None
            else:  # New
                start = timezone.now() + timedelta(days=random.randint(7, 30))
                end = start + timedelta(days=random.randint(180, 365))
                completion = None
            
            org_types = ["Farmers Association", "Fisherfolk Cooperative", "Womens Group", "Livelihood Association"]
            
            project = Project.objects.create(
                project_code=f'{program[:2]}-{mun[:3].upper()}-{random.randint(1000, 9999)}',
                project_title=title,
                project_description=f'Implementation of {tech.lower()} technology for the community of {barangay}, {mun}. This project aims to improve livelihood and productivity of local beneficiaries.',
                agency_grantee=f'{mun} {random.choice(org_types)}',
                mun=mun,
                province='Biliran',
                district='Lone District',
                beneficiary=beneficiary.full_name(),
                beneficiary_address=f'{barangay}, {mun}, Biliran',
                contact_details=beneficiary.contact_number or '09171234567',
                proponent_details=proponent.full_name(),
                program=program,
                status=status,
                year=timezone.now().year if status != 'Completed' else timezone.now().year - 1,
                fund_source=random.choice(budgets).fund_source,
                funds=Decimal(str(funds)),
                total_project_cost=Decimal(str(funds)) * Decimal('1.2'),
                first_tranche=Decimal(str(funds)) * Decimal('0.5'),
                project_start=start.date(),
                project_end=end.date(),
                date_of_completion=completion.date() if completion else None,
                availed_technologies=tech,
                type_of_project=program,
                remarks=f'{status} project in {mun}',
                no_of_beneficiaries=random.randint(20, 100),
                male=random.randint(10, 50),
                female=random.randint(10, 50),
                # Add coordinates with small offset from municipality center
                latitude=coords['lat'] + random.uniform(-0.015, 0.015),
                longitude=coords['lng'] + random.uniform(-0.015, 0.015),
            )
            projects.append(project)
        
        return projects

    def create_tasks(self, projects, users):
        """Create sample tasks for ongoing projects"""
        task_templates = [
            ('Site inspection and validation', 'pending'),
            ('Equipment procurement', 'in_progress'),
            ('Installation and setup', 'pending'),
            ('Training of beneficiaries', 'pending'),
            ('Monitoring and evaluation visit', 'pending'),
            ('Documentation and reporting', 'pending'),
        ]
        
        staff_users = users['staff']
        
        for project in projects:
            if project.status in ['Ongoing', 'New']:
                # Create 2-4 tasks per project
                for template in random.sample(task_templates, random.randint(2, 4)):
                    title, status = template
                    coords = self.MUNICIPALITIES.get(project.mun, {'lat': 11.55, 'lng': 124.47})
                    
                    Task.objects.create(
                        project=project,
                        title=f'{title} - {project.project_title[:30]}',
                        description=f'Task for {project.project_title} in {project.mun}',
                        assigned_to=random.choice(staff_users) if staff_users else None,
                        due_date=timezone.now().date() + timedelta(days=random.randint(7, 90)),
                        status=status,
                        latitude=coords['lat'] + random.uniform(-0.01, 0.01),
                        longitude=coords['lng'] + random.uniform(-0.01, 0.01),
                        location_name=f'{project.mun}, Biliran'
                    )
