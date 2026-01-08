from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_save
from decimal import Decimal

# User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

# ----------------------------
# Custom User Model
# ----------------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('proponent', 'Proponent'),
        ('dost_staff', 'PSTO Staff'),
        ('beneficiary', 'Beneficiary'),
    ]
    
    # TNA Status Choices (for beneficiaries)
    TNA_STATUS_CHOICES = [
        ('not_started', 'TNA Not Started'),
        ('in_progress', 'TNA In Progress'),
        ('completed', 'TNA Completed'),
        ('equipment_selection', 'Equipment Selection'),
        ('procurement', 'Under Procurement'),
        ('delivery_pending', 'Delivery Pending'),
        ('delivered', 'Equipment Delivered'),
        ('operational', 'Operational'),
    ]
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='dost_staff')
    STATUS_CHOICES = [('active', 'Active'), ('deactivated', 'Deactivated')]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    first_name = models.CharField(max_length=50, blank=True, null=True)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=10, blank=True, null=True)
    sex = models.CharField(max_length=6, choices=[('male', 'Male'), ('female', 'Female')], blank=True, null=True)
    civil_status = models.CharField(max_length=10, choices=[('single', 'Single'), ('married', 'Married')], blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    # Beneficiary-specific TNA fields
    tna_status = models.CharField(
        max_length=30, choices=TNA_STATUS_CHOICES, default='not_started',
        help_text='Technology Needs Assessment status for beneficiaries'
    )
    tna_completion_date = models.DateField(blank=True, null=True)
    tna_notes = models.TextField(blank=True, null=True, help_text='Notes from TNA assessment')
    
    objects = CustomUserManager()

    def full_name(self):
        def cap(name): return ' '.join(word.capitalize() for word in name.split()) if name else ''
        first = cap(self.first_name)
        middle = f"{self.middle_name[0].upper()}." if self.middle_name else ''
        last = cap(self.last_name)
        suffix = self.suffix if self.suffix else ''
        return ' '.join(filter(None, [first, middle, last, suffix]))

    def __str__(self): return f"{self.username} ({self.get_role_display()})"
    class Meta: verbose_name = "User"; verbose_name_plural = "Users"

# -------------------------
# Budget Model
# -------------------------
class Budget(models.Model):
    # Equipment Allocation Status - reflects DOST procurement workflow
    STATUS_CHOICES = (
        ('pending_procurement', 'Pending Procurement'),  # Equipment being procured by DOST
        ('available', 'Available for Allocation'),       # Equipment ready to be allocated to projects
        ('partially_allocated', 'Partially Allocated'),  # Some equipment allocated, some available
        ('fully_allocated', 'Fully Allocated'),          # All equipment allocated to projects
        ('completed', 'Completed'),                      # All equipment delivered to beneficiaries
        ('archived', 'Archived'),                        # Historical record
    )

    # DOST Line-Item Budget (LIB) Categories
    LIB_CHOICES = [
        ('PS', 'Personal Services (Salaries/Honoraria)'),
        ('MOOE', 'Maintenance & Other Operating Expenses'),
        ('EO_CO', 'Equipment/Capital Outlay'),
    ]

    # Enhanced Fund Source Choices per DOST standards
    FUND_SOURCE_CHOICES = [
        ('DOST_GIA', 'DOST-GIA (Grants-in-Aid)'),
        ('SETUP', 'SETUP (Small Enterprise Technology Upgrading Program)'),
        ('LOCAL_REGIONAL', 'Local/Regional Funds'),
        ('OTHER', 'Other'),
    ]

    fiscal_year = models.PositiveIntegerField()
    fund_source = models.CharField(max_length=50, choices=FUND_SOURCE_CHOICES, default='DOST_GIA')
    lib_category = models.CharField(max_length=10, choices=LIB_CHOICES, default='PS', help_text="DOST Line-Item Budget Category")

    # Equipment allocation fields
    total_allocated_items = models.PositiveIntegerField(default=0, help_text="Total number of equipment items allocated to this budget")
    total_delivered_items = models.PositiveIntegerField(default=0, help_text="Total number of equipment items delivered from this budget")

    # Monetary value of equipment/materials provided
    total_equipment_value = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Total monetary value of equipment allocated")
    delivered_equipment_value = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Monetary value of equipment delivered")

    # Counterpart Contribution (In-Kind or Monetary)
    counterpart_contribution = models.TextField(blank=True, null=True, help_text="Proponent's counterpart contribution (building space, in-kind services, etc.)")
    counterpart_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Monetary value of counterpart contribution")

    date_allocated = models.DateField(default=timezone.now)
    budget_document = models.FileField(upload_to='budget_documents/', blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending_procurement')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_budgets')
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        """Legacy compatibility property - returns total equipment value"""
        return self.total_equipment_value

    @property
    def remaining_amount(self):
        """Legacy compatibility property - calculates remaining equipment value"""
        return self.total_equipment_value - self.delivered_equipment_value

    def deduct(self, amount):
        """Deduct amount from budget by increasing delivered equipment value"""
        if amount > self.remaining_amount:
            raise ValueError("Cannot deduct more than remaining amount")
        self.delivered_equipment_value += amount
        self.save()

    def __str__(self): return f"{self.fund_source} ({self.fiscal_year})"

# -------------------------
# Proposal Model
# -------------------------
class Proposal(models.Model):
    STATUS_CHOICES = (('pending', 'Pending'), ('for_review', 'For Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('needs_revision', 'Needs Revision'))
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_proposals')
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    proposed_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    approved_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, related_name='proposals', null=True, blank=True)
    document = models.FileField(upload_to='proposals/', blank=True, null=True)
    review_remarks = models.TextField(blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_proposals')
    beneficiary = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='beneficiary_proposals')
    
    # New fields for proponent, beneficiaries, and location
    proponent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='proponent_proposals')
    beneficiaries = models.TextField(blank=True, null=True, help_text="Names of beneficiaries (comma-separated or list)")
    location = models.CharField(max_length=255, blank=True, null=True)
    municipality = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    
    # Location coordinates for map display
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self): return self.title

# -------------------------
# Project (GIA/CEST Schema + Legacy Compatibility)
# -------------------------
class Project(models.Model):
    # --- Schema Fields (GIA/CEST) ---
    no = models.IntegerField(blank=True, null=True)
    project_code = models.CharField(max_length=50, blank=True, null=True)
    agency_grantee = models.CharField(max_length=255, blank=True, null=True)
    mun = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    
    # Primary Details
    project_title = models.TextField(blank=True, null=True)
    # RESTORED FIELD: Essential for existing views
    project_description = models.TextField(blank=True, null=True) 
    
    beneficiary = models.CharField(max_length=255, blank=True, null=True)
    beneficiary_address = models.TextField(blank=True, null=True)
    contact_details = models.TextField(blank=True, null=True)
    proponent_details = models.TextField(blank=True, null=True)
    no_of_beneficiaries = models.IntegerField(blank=True, null=True)
    program = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    donation_status = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    fund_source = models.CharField(max_length=100, blank=True, null=True)
    
    # Dates & Duration
    original_project_duration = models.CharField(max_length=100, blank=True, null=True)
    extension_date = models.CharField(max_length=100, blank=True, null=True)
    
    # Schema-specific date fields
    project_start = models.DateField(blank=True, null=True)
    project_end = models.DateField(blank=True, null=True)
    date_of_release = models.DateField(blank=True, null=True)
    date_of_completion = models.DateField(blank=True, null=True)
    
    # Legacy date fields (Restored for compatibility)
    approval_date = models.DateTimeField(blank=True, null=True) 
    completion_date = models.DateTimeField(blank=True, null=True) 
    
    # Tech
    availed_technologies = models.TextField(blank=True, null=True)
    interventions = models.TextField(blank=True, null=True)
    type_of_project = models.CharField(max_length=100, blank=True, null=True)
    acknowledgment_receipt_by_grantee = models.CharField(max_length=50, blank=True, null=True)
    
    # Financials (New Schema)
    funds = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    check_ada_no = models.CharField(max_length=100, blank=True, null=True)
    status_of_liquidation = models.CharField(max_length=100, blank=True, null=True)
    date_of_liquidation = models.DateField(blank=True, null=True)
    amount_liquidated = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    
    # Tranches / Costs
    first_tranche = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    second_tranche = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    third_tranche = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    dost_viii = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    counterpart_funds = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    total_project_cost = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    internally_managed_fund = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    total_funds_released = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    # Documents / Statuses
    tafr = models.CharField(max_length=50, blank=True, null=True)
    par = models.CharField(max_length=50, blank=True, null=True)
    list_of_eqpt = models.TextField(blank=True, null=True)
    terminal_report = models.CharField(max_length=50, blank=True, null=True)
    invoice_receipt = models.CharField(max_length=50, blank=True, null=True)
    donated = models.CharField(max_length=50, blank=True, null=True)
    date_of_donation = models.DateField(blank=True, null=True)
    counterpart_fund = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    date_of_inspection_tagging = models.DateField(blank=True, null=True)
    pme_visit = models.CharField(max_length=50, blank=True, null=True)
    womens_group = models.CharField(max_length=50, blank=True, null=True)
    
    # Files
    product_photo = models.ImageField(upload_to='project_photos/', blank=True, null=True)
    supporting_documents = models.FileField(upload_to='project_documents/', blank=True, null=True)
    
    # Demographics
    male = models.IntegerField(blank=True, null=True)
    female = models.IntegerField(blank=True, null=True)
    total_beneficiaries = models.IntegerField(blank=True, null=True)
    senior_citizen = models.IntegerField(blank=True, null=True)
    pwd = models.IntegerField(blank=True, null=True)

    # Legacy/Relationship fields (Restored)
    proposal = models.OneToOneField(Proposal, on_delete=models.SET_NULL, null=True, blank=True, related_name='project')
    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, related_name='projects', null=True, blank=True)
    project_leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_projects')
    
    # Legacy Field: 'approved_budget' (Restored as actual field OR property)
    # To strictly fix the error "attribute not found", we can keep it as a property that maps to 'funds', 
    # OR keep it as a separate field if you prefer. Using property is cleaner for data migration.
    # Note: If your database ALREADY has this column, keeping it as a field is safer.
    # I will keep it as a field for now to prevent "no such column" if you didn't migrate yet, 
    # but logically it should map to funds. 
    # For now, I'll rely on the property map below for code compatibility.
    
    # System fields
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    short_duration_notified = models.BooleanField(default=False)
    
    # Location coordinates for map display
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # ----------------------------------------------------
    # COMPATIBILITY LAYER (Properties & Setters)
    # This prevents 'AttributeError' in old views/signals
    # ----------------------------------------------------
    
    @property
    def approved_budget(self):
        # Maps old 'approved_budget' to new 'funds'
        return self.funds or Decimal('0.00')
    
    @approved_budget.setter
    def approved_budget(self, value):
        self.funds = value

    @property
    def start_date(self):
        # Maps old 'start_date' to new 'project_start'
        return self.project_start
    
    @start_date.setter
    def start_date(self, value):
        self.project_start = value
    
    @property
    def end_date(self):
        # Maps old 'end_date' to new 'project_end'
        return self.project_end

    @end_date.setter
    def end_date(self, value):
        self.project_end = value

    def __str__(self):
        code = self.project_code if self.project_code else "No Code"
        return f"{self.project_title} ({code})"

    @property
    def total_expenses(self):
        agg = self.expenses.aggregate(total=Sum('expense_amount'))['total']
        return agg or Decimal('0.00')

    @property
    def remaining_project_amount(self):
        # Calculated from funds vs expenses
        funds = self.funds or Decimal('0.00')
        return (funds - self.total_expenses).quantize(Decimal('0.01'))


# -------------------------
# Budget Transaction
# -------------------------
class BudgetTransaction(models.Model):
    TYPE_CHOICES = [('allocation', 'Allocation'), ('deduction', 'Deduction'), ('reallocation', 'Reallocation'), ('refund', 'Refund')]
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transactions')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='processed_transactions')
    date_transaction = models.DateTimeField(auto_now_add=True)

# -------------------------
# Project Expense
# -------------------------
class ProjectExpense(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    expense_title = models.CharField(max_length=255)
    expense_amount = models.DecimalField(max_digits=18, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)
    receipt_document = models.FileField(upload_to='project_receipts/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_expenses')
    date_created = models.DateTimeField(auto_now_add=True)


# -------------------------
# Project Tranche (DOST Tranche Tracking - matches migration)
# -------------------------
class ProjectTranche(models.Model):
    """Track tranche allocations and releases for projects"""
    TRANCHE_CHOICES = [
        ('tranche_1', 'Tranche 1'),
        ('tranche_2', 'Tranche 2'),
        ('tranche_3', 'Tranche 3'),
    ]
    
    LIQUIDATION_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('audited', 'Audited'),
    ]
    
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tranches'
    )
    tranche_number = models.CharField(max_length=20, choices=TRANCHE_CHOICES)
    allocated_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text='Amount allocated for this tranche'
    )
    released_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text='Amount actually released'
    )
    release_date = models.DateField(blank=True, null=True)
    check_number = models.CharField(max_length=100, blank=True, null=True)
    ada_number = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='ADA (Authority to Debit Account) number'
    )
    liquidation_status = models.CharField(
        max_length=20, choices=LIQUIDATION_STATUS_CHOICES, default='not_started'
    )
    liquidation_date = models.DateField(blank=True, null=True)
    amount_liquidated = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    utilization_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text='Percentage of funds utilized'
    )
    justification = models.TextField(
        default='Tranche allocation for project implementation',
        help_text='Justification for this tranche allocation'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_tranches'
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['project', 'tranche_number']
        unique_together = ['project', 'tranche_number']
    
    def __str__(self):
        return f"{self.project.title} - {self.get_tranche_number_display()}"
    
    @property
    def liquidation_percentage(self):
        """Calculate percentage of tranche liquidated"""
        if self.allocated_amount and self.allocated_amount > 0:
            return round((self.amount_liquidated / self.allocated_amount) * 100, 2)
        return Decimal('0.00')


# -------------------------
# Tranche Release (DOST Fund Release Tracking)
# -------------------------
class TrancheRelease(models.Model):
    """Track individual tranche releases for DOST projects with liquidation status"""
    TRANCHE_CHOICES = [
        (1, '1st Tranche'),
        (2, '2nd Tranche'),
        (3, '3rd Tranche'),
        (4, '4th Tranche'),
        (5, '5th Tranche'),
    ]
    
    LIQUIDATION_STATUS_CHOICES = [
        ('pending', 'Pending Liquidation'),
        ('partial', 'Partially Liquidated'),
        ('submitted', 'Liquidation Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Liquidation Approved'),
        ('rejected', 'Liquidation Rejected'),
    ]
    
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tranche_releases'
    )
    tranche_number = models.PositiveIntegerField(choices=TRANCHE_CHOICES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    release_date = models.DateField(blank=True, null=True)
    check_number = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Check/ADA number for the release'
    )
    bank_account = models.CharField(max_length=100, blank=True, null=True)
    
    # Liquidation tracking
    liquidation_status = models.CharField(
        max_length=20, choices=LIQUIDATION_STATUS_CHOICES, default='pending'
    )
    liquidation_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal('0.00'),
        help_text='Amount liquidated so far'
    )
    liquidation_date = models.DateField(blank=True, null=True)
    liquidation_document = models.FileField(
        upload_to='liquidation_documents/', blank=True, null=True
    )
    
    # Eligibility for next tranche
    is_released = models.BooleanField(default=False)
    eligible_for_next_tranche = models.BooleanField(
        default=False,
        help_text='Automatically set when liquidation is approved'
    )
    
    # Milestone requirements
    required_liquidation_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('80.00'),
        help_text='Required percentage of liquidation before next tranche'
    )
    
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_tranche_releases'
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['project', 'tranche_number']
        unique_together = ['project', 'tranche_number']
        verbose_name = 'Tranche Release'
        verbose_name_plural = 'Tranche Releases'
    
    def __str__(self):
        return f"{self.project.title} - {self.get_tranche_number_display()}"
    
    @property
    def liquidation_percentage(self):
        """Calculate percentage of tranche liquidated"""
        if self.amount and self.amount > 0:
            return round((self.liquidation_amount / self.amount) * 100, 2)
        return Decimal('0.00')
    
    @property
    def remaining_to_liquidate(self):
        """Calculate remaining amount to liquidate"""
        return self.amount - self.liquidation_amount
    
    @property
    def meets_liquidation_requirement(self):
        """Check if liquidation meets requirement for next tranche"""
        return self.liquidation_percentage >= self.required_liquidation_percentage
    
    def update_eligibility(self):
        """Update eligibility for next tranche based on liquidation status"""
        if self.liquidation_status == 'approved' and self.meets_liquidation_requirement:
            self.eligible_for_next_tranche = True
        else:
            self.eligible_for_next_tranche = False
        self.save(update_fields=['eligible_for_next_tranche'])


# -------------------------
# Document Models for Multiple File Uploads
# -------------------------
class BudgetDocument(models.Model):
    """Stores multiple documents for a Budget"""
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='budget_documents/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} - {self.budget}"


class ProposalDocument(models.Model):
    """Stores multiple documents for a Proposal"""
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='proposals/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} - {self.proposal}"


class ProjectDocument(models.Model):
    """Stores multiple documents/photos for a Project"""
    DOCUMENT_TYPES = [
        ('supporting', 'Supporting Document'),
        ('photo', 'Product Photo'),
        ('other', 'Other'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='project_documents/')
    filename = models.CharField(max_length=255, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='supporting')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} - {self.project}"


class ExpenseDocument(models.Model):
    """Stores multiple receipt documents for a ProjectExpense"""
    expense = models.ForeignKey(ProjectExpense, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='project_receipts/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filename} - {self.expense}"


# -------------------------
# Approval Log
# -------------------------
class ApprovalLog(models.Model):
    ACTION_CHOICES = [('approved', 'Approved'), ('rejected', 'Rejected'), ('revision_requested', 'Revision Requested'), ('for_review', 'For Review')]
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='approval_logs')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approval_actions')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

# -------------------------
# Task
# -------------------------
class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), 
        ('in_progress', 'In Progress'), 
        ('completed', 'Completed'), 
        ('delayed', 'Delayed'),
        ('on_track', 'On Track'),
        ('behind_schedule', 'Behind Schedule'),
        ('at_risk', 'At Risk')
    ]
    PRIORITY_CHOICES = [('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    CATEGORY_CHOICES = [
        ('planning', 'Planning'),
        ('development', 'Development'),
        ('testing', 'Testing'),
        ('documentation', 'Documentation'),
        ('review', 'Review'),
        ('deployment', 'Deployment'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField()
    completion_date = models.DateField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    progress_percentage = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Estimated hours to complete")
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Actual hours worked")
    due_date_notified = models.BooleanField(default=False)

# -------------------------
# Audit Log
# -------------------------
class AuditLog(models.Model):
    ACTION_TYPES = [
        ('create', 'Create'), 
        ('update', 'Update'), 
        ('delete', 'Delete'), 
        ('login', 'Login'), 
        ('logout', 'Logout'),
        ('status_change', 'Status Change'),
        ('approval', 'Approval'),
        ('rejection', 'Rejection'),
        ('transfer', 'Transfer'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    details = models.TextField(null=True, blank=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # DOST Compliance: Justification/Reason for the action
    reason = models.TextField(
        blank=True, null=True,
        help_text='Justification or reason for this action (required for sensitive operations)'
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"

# -------------------------
# Notification
# -------------------------
class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('task', 'Task'),
        ('project', 'Project'),
        ('chat', 'Group Chat'),
        ('announcement', 'Announcement'),
        ('budget', 'Budget'),
        ('proposal', 'Proposal'),
    ]
    STATUS_CHOICES = [('unread', 'Unread'), ('read', 'Read')]
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notifications')
    message = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    link = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    timestamp = models.DateTimeField(default=timezone.now)

# -------------------------
# Form Template (Downloadable Forms)
# -------------------------
class FormTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('proposal', 'Proposal Forms'),
        ('project', 'Project Forms'),
        ('financial', 'Financial Forms'),
        ('report', 'Report Forms'),
        ('compliance', 'Compliance Forms'),
        ('other', 'Other Forms'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    file = models.FileField(upload_to='form_templates/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date_uploaded']
    
    def __str__(self):
        return self.title
    
    @property
    def file_extension(self):
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return ''
    
    @property
    def file_size(self):
        if self.file:
            try:
                size = self.file.size
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                else:
                    return f"{size / (1024 * 1024):.1f} MB"
            except:
                return "Unknown"
        return "Unknown"

# -------------------------
# Extension Request Model
# -------------------------
class ExtensionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='extension_requests')
    proponent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='extension_requests')
    reason = models.TextField(blank=True, null=True)
    requested_extension_days = models.PositiveIntegerField(blank=True, null=True)
    letter = models.FileField(upload_to='extension_letters/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    approved_days = models.PositiveIntegerField(blank=True, null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='approved_extension_requests')
    date_submitted = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateTimeField(blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Extension Request for {self.proposal.title} by {self.proponent.full_name()}"

    def can_user_access(self, user):
        # Only the proponent and any admin can access
        return user == self.proponent or user.role == 'admin'

# -------------------------
# Signals
# -------------------------
@receiver(pre_save, sender=Proposal)
def proposal_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Proposal.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except Proposal.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

@receiver(post_save, sender=Proposal)
def proposal_post_save(sender, instance, created, **kwargs):
    prev = getattr(instance, '_previous_status', None)
    if prev == 'approved' or instance.status != 'approved':
        return

    approved_amt = instance.approved_amount or instance.proposed_amount
    if not instance.budget:
        return # Optionally log warning

    with transaction.atomic():
        budget = Budget.objects.select_for_update().get(pk=instance.budget.pk)
        if budget.remaining_amount < approved_amt:
            # Logic handled in view, but safety check here
            return 

        budget.deduct(approved_amt)

        # Create Project using mapped fields
        try:
            # Check if project exists (via OneToOne)
            project = instance.project
        except Project.DoesNotExist:
            Project.objects.create(
                proposal=instance,
                project_title=instance.title,
                project_description=instance.description, # Mapped correctly now
                funds=approved_amt,
                budget=budget,
                project_leader=instance.submitted_by,
                status='ongoing',
                project_start=timezone.now().date(),
                # Copy location data from proposal
                mun=instance.municipality,
                province=instance.province,
                beneficiary_address=instance.location,
                latitude=instance.latitude,
                longitude=instance.longitude
            )
        
        # Log Transaction
        BudgetTransaction.objects.create(
            budget=budget,
            project=instance.project if hasattr(instance, 'project') else None,
            transaction_type='deduction',
            amount=approved_amt,
            description=f"Auto-deduction for approved proposal {instance.title}",
            processed_by=instance.submitted_by
        )

# -------------------------
# Personal Task Model (Staff Personal Checklists)
# -------------------------
class PersonalTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_tasks')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='personal_tasks')
    title = models.CharField(max_length=255, help_text="Project-specific task title")
    checklist = models.JSONField(default=list, help_text="List of checklist items with format: [{'text': 'task description', 'completed': false}, ...]")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Personal Task"
        verbose_name_plural = "Personal Tasks"
    
    def __str__(self):
        return f"{self.user.username}: {self.title} ({self.project.project_title})"
    
    def add_checklist_item(self, text):
        """Add a new checklist item"""
        if not self.checklist:
            self.checklist = []
        self.checklist.append({'text': text, 'completed': False})
        self.save(update_fields=['checklist', 'updated_at'])
    
    def toggle_checklist_item(self, index):
        """Toggle completion status of a checklist item"""
        if 0 <= index < len(self.checklist):
            self.checklist[index]['completed'] = not self.checklist[index]['completed']
            self.save(update_fields=['checklist', 'updated_at'])
            self.update_status_from_checklist()
    
    def update_status_from_checklist(self):
        """Update task status based on checklist completion"""
        if not self.checklist:
            return
        
        completed_items = sum(1 for item in self.checklist if item['completed'])
        total_items = len(self.checklist)
        
        if completed_items == 0:
            self.status = 'pending'
        elif completed_items == total_items:
            self.status = 'completed'
            self.completed_at = timezone.now()
        else:
            self.status = 'in_progress'
        
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def get_checklist_progress(self):
        """Return tuple of (completed_count, total_count)"""
        if not self.checklist:
            return (0, 0)
        completed = sum(1 for item in self.checklist if item['completed'])
        return (completed, len(self.checklist))
    
    def mark_completed(self):
        """Mark task as completed and set completion timestamp"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def mark_pending(self):
        """Mark task as pending and clear completion timestamp"""
        self.status = 'pending'
        self.completed_at = None
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

# -------------------------------
# Communication Hub Models
# -------------------------------

class Message(models.Model):
    """Direct messaging between users"""
    MESSAGE_TYPES = [
        ('direct', 'Direct Message'),
        ('system', 'System Message'),
        ('announcement', 'Announcement'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='direct')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} to {self.recipient.get_full_name()}: {self.subject}"

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

class GroupChat(models.Model):
    """Group chat rooms for project teams"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='group_chats', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_group_chats')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def get_members(self):
        """Get all active members of the group chat"""
        return self.members.filter(is_active=True).select_related('user')

class GroupChatMember(models.Model):
    """Members of group chats"""
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('admin', 'Administrator'),
    ]

    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_chat_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['group_chat', 'user']
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.group_chat.name}"

class GroupChatMessage(models.Model):
    """Messages in group chats"""
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_chat_messages')
    content = models.TextField()
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group_chat', 'created_at']),
        ]

    def __str__(self):
        return f"Message by {self.sender.get_full_name()} in {self.group_chat.name}"

class Announcement(models.Model):
    """System-wide announcements"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Recipients (for targeted announcements)
    target_roles = models.JSONField(default=list, blank=True)  # List of user roles
    target_users = models.ManyToManyField(User, related_name='targeted_announcements', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_expired(self):
        """Check if announcement has expired"""
        return self.expires_at and timezone.now() > self.expires_at

    def get_recipients(self):
        """Get all users who should receive this announcement"""
        if self.target_users.exists():
            return self.target_users.all()
        elif self.target_roles:
            return User.objects.filter(role__in=self.target_roles, status='active')
        else:
            return User.objects.filter(status='active')


# -------------------------------
# One-Sided Delete Tracking Models
# -------------------------------

class DeletedMessage(models.Model):
    """Track which messages have been deleted by which user (one-sided delete)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deleted_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='deleted_by_users')
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'message']

    def __str__(self):
        return f"Message {self.message.id} deleted by {self.user.get_full_name()}"


class DeletedConversation(models.Model):
    """Track which conversations have been deleted by which user (one-sided delete)
    A conversation is defined as all messages between two users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deleted_conversations')
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_deleted_by')
    deleted_at = models.DateTimeField(auto_now_add=True)
    # Messages sent before this time are considered deleted for this user
    delete_before = models.DateTimeField()

    class Meta:
        unique_together = ['user', 'partner']

    def __str__(self):
        return f"Conversation with {self.partner.get_full_name()} deleted by {self.user.get_full_name()}"


class DeletedGroupChat(models.Model):
    """Track which group chats have been deleted/hidden by which user (one-sided)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deleted_group_chats')
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='deleted_by_users')
    deleted_at = models.DateTimeField(auto_now_add=True)
    # Messages sent before this time are considered deleted for this user
    delete_before = models.DateTimeField()

    class Meta:
        unique_together = ['user', 'group_chat']

    def __str__(self):
        return f"GroupChat {self.group_chat.name} deleted by {self.user.get_full_name()}"


class DeletedGroupChatMessage(models.Model):
    """Track which group chat messages have been deleted by which user (one-sided)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deleted_group_messages')
    message = models.ForeignKey(GroupChatMessage, on_delete=models.CASCADE, related_name='deleted_by_users')
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'message']

    def __str__(self):
        return f"Group message {self.message.id} deleted by {self.user.get_full_name()}"


# -------------------------------
# System Health Monitoring Models
# -------------------------------

class SystemHealth(models.Model):
    """System health metrics and status"""
    METRIC_TYPES = [
        ('cpu_usage', 'CPU Usage'),
        ('memory_usage', 'Memory Usage'),
        ('disk_usage', 'Disk Usage'),
        ('database_connections', 'Database Connections'),
        ('active_users', 'Active Users'),
        ('response_time', 'Response Time'),
        ('network_latency', 'Network Latency'),
        ('uptime', 'System Uptime'),
        ('error_rate', 'Error Rate'),
        ('queue_length', 'Queue Length'),
    ]

    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default='percent')  # percent, mb, seconds, count
    status = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], default='healthy')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', 'recorded_at']),
        ]

    def __str__(self):
        return f"{self.metric_type}: {self.value} {self.unit} ({self.status})"

class BackupStatus(models.Model):
    """Database backup status tracking"""
    BACKUP_TYPES = [
        ('full', 'Full Backup'),
        ('incremental', 'Incremental Backup'),
        ('manual', 'Manual Backup'),
        ('scheduled', 'Scheduled Backup'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.backup_type} backup - {self.status}"

    def duration(self):
        """Calculate backup duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

class MaintenanceSchedule(models.Model):
    """Scheduled system maintenance tasks"""
    MAINTENANCE_TYPES = [
        ('database_cleanup', 'Database Cleanup'),
        ('file_cleanup', 'File Cleanup'),
        ('system_update', 'System Update'),
        ('security_scan', 'Security Scan'),
        ('performance_optimization', 'Performance Optimization'),
        ('backup_verification', 'Backup Verification'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    maintenance_type = models.CharField(max_length=50, choices=MAINTENANCE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.DurationField(null=True, blank=True)  # Expected duration
    actual_duration = models.DurationField(null=True, blank=True)  # Actual duration
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_maintenance')
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=100, blank=True)  # cron-like pattern
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.title} - {self.scheduled_at}"

    def is_overdue(self):
        """Check if maintenance is overdue"""
        return self.status == 'scheduled' and timezone.now() > self.scheduled_at

    def can_start(self):
        """Check if maintenance can be started"""
        return self.status == 'scheduled' and timezone.now() >= self.scheduled_at

# -------------------------------
# Equipment Management Models
# -------------------------------
class EquipmentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Equipment Categories'

    def __str__(self):
        return self.name


class EquipmentItem(models.Model):
    UNIT_CHOICES = [
        ('pieces', 'Pieces'),
        ('sets', 'Sets'),
        ('units', 'Units'),
        ('kg', 'Kilograms'),
        ('liters', 'Liters'),
        ('meters', 'Meters'),
        ('boxes', 'Boxes'),
        ('packs', 'Packs'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pieces')
    estimated_unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text='Estimated cost per unit for reference'
    )
    specifications = models.TextField(
        blank=True, null=True,
        help_text='Technical specifications, model numbers, etc.'
    )
    date_created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(
        EquipmentCategory, on_delete=models.CASCADE,
        related_name='items'
    )

    class Meta:
        unique_together = [('name', 'category')]

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class BudgetAllocation(models.Model):
    STATUS_CHOICES = [
        ('allocated', 'Allocated'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    allocated_quantity = models.PositiveIntegerField()
    delivered_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='allocated'
    )
    allocation_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    # Foreign Keys
    budget = models.ForeignKey(
        Budget, on_delete=models.CASCADE, related_name='allocations'
    )
    equipment_item = models.ForeignKey(
        EquipmentItem, on_delete=models.CASCADE, related_name='allocations'
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='equipment_allocations'
    )

    class Meta:
        unique_together = [('budget', 'equipment_item')]

    @property
    def allocated_value(self):
        """Calculate total allocated value for this allocation"""
        return self.allocated_quantity * (self.equipment_item.estimated_unit_cost or 0)

    @property
    def delivered_value(self):
        """Calculate total delivered value for this allocation"""
        return self.delivered_quantity * (self.equipment_item.estimated_unit_cost or 0)

    @property
    def remaining_quantity(self):
        """Calculate remaining quantity to be delivered"""
        return self.allocated_quantity - self.delivered_quantity

    def __str__(self):
        return f"{self.equipment_item.name} - {self.allocated_quantity} {self.equipment_item.unit}"


class ProjectEquipment(models.Model):
    STATUS_CHOICES = [
        ('delivered', 'Delivered'),
        ('installed', 'Installed'),
        ('operational', 'Operational'),
        ('returned', 'Returned'),
        ('damaged', 'Damaged'),
    ]
    
    # DOST SETUP Ownership Status Choices
    OWNERSHIP_STATUS_CHOICES = [
        ('dost_owned', 'DOST-Owned (Under Lease)'),
        ('transfer_pending', 'Transfer Pending'),
        ('beneficiary_owned', 'Beneficiary-Owned'),
    ]

    delivered_quantity = models.PositiveIntegerField()
    delivery_date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='delivered'
    )
    serial_numbers = models.TextField(
        blank=True, null=True,
        help_text='Serial numbers, batch numbers, etc.'
    )
    condition_notes = models.TextField(blank=True, null=True)
    received_by = models.CharField(max_length=255, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    # DOST Compliance Fields
    property_tag_number = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='DOST Property Tag Number for inventory audits (e.g., DOST-R10-2024-001)'
    )
    lease_start_date = models.DateField(
        blank=True, null=True,
        help_text='Start date of 3-year SETUP equipment lease period'
    )
    ownership_status = models.CharField(
        max_length=20, choices=OWNERSHIP_STATUS_CHOICES, default='dost_owned',
        help_text='Equipment ownership status for SETUP projects'
    )
    ownership_transfer_date = models.DateField(
        blank=True, null=True,
        help_text='Date when ownership was transferred to beneficiary'
    )

    # Foreign Keys
    budget_allocation = models.ForeignKey(
        BudgetAllocation, on_delete=models.CASCADE, related_name='deliveries'
    )
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='equipment_deliveries'
    )
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='equipment_deliveries'
    )

    class Meta:
        verbose_name_plural = 'Project Equipment'

    def __str__(self):
        return f"{self.budget_allocation.equipment_item.name} - {self.project.title}"
    
    @property
    def ownership_end_date(self):
        """Calculate when 3-year SETUP lease ends and ownership can transfer"""
        if self.lease_start_date:
            from datetime import timedelta
            return self.lease_start_date + timedelta(days=365 * 3)
        return None
    
    @property
    def days_until_ownership(self):
        """Calculate remaining days until ownership can be transferred"""
        if self.ownership_end_date and self.ownership_status == 'dost_owned':
            from datetime import date
            remaining = (self.ownership_end_date - date.today()).days
            return max(0, remaining)
        return 0
    
    @property
    def ownership_progress_percentage(self):
        """Calculate percentage of 3-year lease period completed"""
        if self.lease_start_date:
            from datetime import date
            total_days = 365 * 3  # 3 years
            elapsed_days = (date.today() - self.lease_start_date).days
            percentage = min(100, max(0, (elapsed_days / total_days) * 100))
            return round(percentage, 1)
        return 0
    
    @property
    def is_eligible_for_transfer(self):
        """Check if equipment is eligible for ownership transfer"""
        if self.ownership_end_date:
            from datetime import date
            return date.today() >= self.ownership_end_date and self.ownership_status == 'dost_owned'
        return False


# Signals to update budget totals when allocations change
@receiver(post_save, sender=BudgetAllocation)
def update_budget_totals_on_allocation_save(sender, instance, **kwargs):
    """Update budget equipment totals when allocation is created or modified"""
    budget = instance.budget
    # Calculate total allocated value from all allocations
    allocations = BudgetAllocation.objects.filter(budget=budget).select_related('equipment_item')
    total_allocated = sum(
        alloc.allocated_quantity * (alloc.equipment_item.estimated_unit_cost or 0)
        for alloc in allocations
    )
    
    # Calculate total delivered value from project equipment deliveries
    deliveries = ProjectEquipment.objects.filter(
        budget_allocation__budget=budget
    ).select_related('budget_allocation__equipment_item')
    total_delivered = sum(
        delivery.delivered_quantity * (delivery.budget_allocation.equipment_item.estimated_unit_cost or 0)
        for delivery in deliveries
    )
    
    budget.total_equipment_value = Decimal(str(total_allocated))
    budget.delivered_equipment_value = Decimal(str(total_delivered))
    budget.save(update_fields=['total_equipment_value', 'delivered_equipment_value'])


@receiver(post_delete, sender=BudgetAllocation)
def update_budget_totals_on_allocation_delete(sender, instance, **kwargs):
    """Update budget equipment totals when allocation is deleted"""
    budget = instance.budget
    # Recalculate totals after deletion
    allocations = BudgetAllocation.objects.filter(budget=budget).select_related('equipment_item')
    total_allocated = sum(
        alloc.allocated_quantity * (alloc.equipment_item.estimated_unit_cost or 0)
        for alloc in allocations
    )
    
    deliveries = ProjectEquipment.objects.filter(
        budget_allocation__budget=budget
    ).select_related('budget_allocation__equipment_item')
    total_delivered = sum(
        delivery.delivered_quantity * (delivery.budget_allocation.equipment_item.estimated_unit_cost or 0)
        for delivery in deliveries
    )
    
    budget.total_equipment_value = Decimal(str(total_allocated))
    budget.delivered_equipment_value = Decimal(str(total_delivered))
    budget.save(update_fields=['total_equipment_value', 'delivered_equipment_value'])


@receiver(post_save, sender=ProjectEquipment)
def update_budget_delivered_on_delivery_save(sender, instance, **kwargs):
    """Update budget delivered totals when equipment is delivered to projects"""
    budget = instance.budget_allocation.budget
    # Recalculate delivered total
    deliveries = ProjectEquipment.objects.filter(
        budget_allocation__budget=budget
    ).select_related('budget_allocation__equipment_item')
    total_delivered = sum(
        delivery.delivered_quantity * (delivery.budget_allocation.equipment_item.estimated_unit_cost or 0)
        for delivery in deliveries
    )
    
    budget.delivered_equipment_value = Decimal(str(total_delivered))
    budget.save(update_fields=['delivered_equipment_value'])


@receiver(post_delete, sender=ProjectEquipment)
def update_budget_delivered_on_delivery_delete(sender, instance, **kwargs):
    """Update budget delivered totals when equipment delivery is removed"""
    budget = instance.budget_allocation.budget
    # Recalculate delivered total
    deliveries = ProjectEquipment.objects.filter(
        budget_allocation__budget=budget
    ).select_related('budget_allocation__equipment_item')
    total_delivered = sum(
        delivery.delivered_quantity * (delivery.budget_allocation.equipment_item.estimated_unit_cost or 0)
        for delivery in deliveries
    )
    
    budget.delivered_equipment_value = Decimal(str(total_delivered))
    budget.save(update_fields=['delivered_equipment_value'])


# -------------------------------
# Task Time Entry (Time Tracking)
# -------------------------------


# ===============================
# DIGITAL SIGNATURE MODEL (#24)
# ===============================
class DigitalSignature(models.Model):
    """Store digital signatures for document approvals"""
    SIGNATURE_TYPE_CHOICES = [
        ('approval', 'Approval Signature'),
        ('endorsement', 'Endorsement Signature'),
        ('certification', 'Certification Signature'),
        ('acknowledgment', 'Acknowledgment Signature'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='signatures')
    signature_image = models.ImageField(upload_to='signatures/', blank=True, null=True)
    signature_data = models.TextField(blank=True, null=True, help_text='Base64 encoded signature drawing')
    signature_type = models.CharField(max_length=20, choices=SIGNATURE_TYPE_CHOICES, default='approval')
    
    # Link to documents
    content_type = models.CharField(max_length=50, help_text='Model type: proposal, project, extension_request')
    object_id = models.PositiveIntegerField(help_text='ID of the signed document')
    
    # Metadata
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    device_info = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    # Verification
    verification_hash = models.CharField(max_length=64, blank=True, null=True, help_text='SHA256 hash for verification')
    is_verified = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-signed_at']
        verbose_name = 'Digital Signature'
        verbose_name_plural = 'Digital Signatures'
    
    def __str__(self):
        return f"Signature by {self.user.username} on {self.content_type} #{self.object_id}"


# ===============================
# CALENDAR EVENT MODEL (#17)
# ===============================
class CalendarEvent(models.Model):
    """Store calendar events for tasks, deadlines, and milestones"""
    EVENT_TYPE_CHOICES = [
        ('task', 'Task'),
        ('deadline', 'Deadline'),
        ('milestone', 'Milestone'),
        ('meeting', 'Meeting'),
        ('reminder', 'Reminder'),
        ('holiday', 'Holiday'),
    ]
    
    COLOR_CHOICES = [
        ('#3b82f6', 'Blue'),
        ('#10b981', 'Green'),
        ('#f59e0b', 'Yellow'),
        ('#ef4444', 'Red'),
        ('#8b5cf6', 'Purple'),
        ('#ec4899', 'Pink'),
        ('#6b7280', 'Gray'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='task')
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='#3b82f6')
    
    # Date/Time
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    all_day = models.BooleanField(default=True)
    
    # Relations
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calendar_events')
    project = models.ForeignKey('Project', on_delete=models.CASCADE, blank=True, null=True, related_name='calendar_events')
    task = models.ForeignKey('Task', on_delete=models.CASCADE, blank=True, null=True, related_name='calendar_events')
    
    # Visibility
    is_public = models.BooleanField(default=False, help_text='Visible to all users')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='event_participations')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date', 'start_time']
        verbose_name = 'Calendar Event'
        verbose_name_plural = 'Calendar Events'
    
    def __str__(self):
        return f"{self.title} ({self.start_date})"


# ===============================
# MENTION MODEL (#16)
# ===============================
class Mention(models.Model):
    """Track @mentions in messages and comments"""
    mentioned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentions_received')
    mentioned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentions_made')
    
    # Context
    content_type = models.CharField(max_length=50, help_text='message, group_chat_message, announcement')
    object_id = models.PositiveIntegerField()
    message_preview = models.CharField(max_length=255, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mention'
        verbose_name_plural = 'Mentions'
    
    def __str__(self):
        return f"@{self.mentioned_user.username} by {self.mentioned_by.username}"


# ===============================
# PROJECT MILESTONE MODEL (for Gantt Chart #18)
# ===============================
class ProjectMilestone(models.Model):
    """Project milestones for Gantt chart visualization"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]
    
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Dates
    planned_start = models.DateField()
    planned_end = models.DateField()
    actual_start = models.DateField(blank=True, null=True)
    actual_end = models.DateField(blank=True, null=True)
    
    # Progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.PositiveIntegerField(default=0, help_text='0-100%')
    
    # Dependencies
    depends_on = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='dependents')
    order = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['project', 'order', 'planned_start']
        verbose_name = 'Project Milestone'
        verbose_name_plural = 'Project Milestones'
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    @property
    def is_overdue(self):
        if self.status != 'completed' and self.planned_end < timezone.now().date():
            return True
        return False


# ===============================
# TRANSLATION MODEL (#21)
# ===============================
class Translation(models.Model):
    """Store translations for multi-language support"""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fil', 'Filipino'),
    ]
    
    key = models.CharField(max_length=255, help_text='Unique translation key')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    text = models.TextField()
    context = models.CharField(max_length=100, blank=True, null=True, help_text='e.g., menu, button, message')
    
    class Meta:
        unique_together = ['key', 'language']
        ordering = ['key', 'language']
        verbose_name = 'Translation'
        verbose_name_plural = 'Translations'
    
    def __str__(self):
        return f"{self.key} ({self.language})"


# ===============================
# USER LANGUAGE PREFERENCE
# ===============================
class UserPreference(models.Model):
    """Store user preferences including language"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences')
    language = models.CharField(max_length=5, choices=Translation.LANGUAGE_CHOICES, default='en')
    simple_mode = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
