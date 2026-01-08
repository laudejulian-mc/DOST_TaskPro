from django.contrib import admin
from .models import (
    User, Budget, Proposal, Project,
    ProjectExpense, BudgetTransaction, ApprovalLog, Task, AuditLog, Notification,
    BudgetDocument, ProposalDocument, ProjectDocument, ExpenseDocument, ExtensionRequest,
    PersonalTask, Message, GroupChat, GroupChatMember, GroupChatMessage, Announcement,
    SystemHealth, BackupStatus, MaintenanceSchedule,
    EquipmentItem, EquipmentCategory, BudgetAllocation, ProjectEquipment, TrancheRelease
)

# ------------------------
# Custom User Admin
# ------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'role', 'status', 'tna_status', 'date_created')
    list_filter = ('role', 'status', 'sex', 'civil_status', 'tna_status')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('date_created', 'date_updated')
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'password', 'email', 'role', 'status')
        }),
        ('Personal Details', {
            'fields': (
                'first_name', 'middle_name', 'last_name', 'suffix',
                'sex', 'civil_status', 'contact_number', 'address',
                'profile_picture'
            )
        }),
        ('TNA Information (Beneficiaries)', {
            'fields': ('tna_status', 'tna_completion_date', 'tna_notes'),
            'classes': ('collapse',),
            'description': 'Technology Needs Assessment tracking for beneficiary users'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Timestamps', {
            'fields': ('last_login', 'date_joined', 'date_created', 'date_updated')
        }),
    )


# ------------------------
# Budget Admin
# ------------------------
@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('fund_source', 'fiscal_year', 'total_amount', 'remaining_amount', 'status', 'date_allocated')
    search_fields = ('fund_source',)
    list_filter = ('status', 'fiscal_year')
    readonly_fields = ('date_created', 'date_updated')
    fieldsets = (
        ('Budget Information', {
            'fields': ('fund_source', 'fiscal_year', 'total_amount', 'remaining_amount', 'status', 'budget_document')
        }),
        ('Audit Trail', {
            'fields': ('created_by', 'date_allocated', 'date_created', 'date_updated')
        }),
    )


# ------------------------
# Proposal Admin
# ------------------------
@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'proposed_amount', 'approved_amount', 'status', 'submission_date', 'processed_by')
    list_filter = ('status', 'submission_date')
    search_fields = ('title', 'submitted_by__username', 'budget__fund_source')
    readonly_fields = ('submission_date', 'date_updated')
    fieldsets = (
        ('Proposal Details', {
            'fields': ('title', 'description', 'submitted_by', 'document', 'processed_by')
        }),
        ('Budget & Funding', {
            'fields': ('proposed_amount', 'approved_amount', 'budget')
        }),
        ('Review & Status', {
            'fields': ('status', 'review_remarks')
        }),
        ('Timestamps', {
            'fields': ('submission_date', 'date_updated')
        }),
    )


# ------------------------
# Project Admin (UPDATED for GIA/CEST Schema)
# ------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    # Updated list_display to match the SQL schema columns you requested
    list_display = (
        'no', 
        'project_code', 
        'project_title', 
        'agency_grantee', 
        'province', 
        'fund_source', 
        'funds', 
        'status'
    )
    
    # Updated filters based on schema fields
    list_filter = ('status', 'year', 'province', 'district', 'fund_source')
    
    # Updated search fields
    search_fields = ('project_title', 'project_code', 'agency_grantee', 'beneficiary', 'mun', 'province')
    
    # Updated readonly fields (removed invalid fields from legacy model)
    readonly_fields = ('date_created', 'date_updated')

    # Reorganized fieldsets to match the new large schema
    fieldsets = (
        ('Project Identification', {
            'fields': ('no', 'project_code', 'year', 'type_of_project', 'program', 'status')
        }),
        ('Basic Information', {
            'fields': ('project_title', 'agency_grantee', 'proponent_details', 'remarks')
        }),
        ('Location', {
            'fields': ('province', 'district', 'mun')
        }),
        ('Beneficiaries', {
            'fields': ('beneficiary', 'beneficiary_address', 'no_of_beneficiaries', 'contact_details', 'male', 'female', 'senior_citizen', 'pwd', 'total_beneficiaries')
        }),
        ('Financials', {
            'fields': ('fund_source', 'funds', 'total_project_cost', 'counterpart_funds', 'internally_managed_fund', 'total_funds_released')
        }),
        ('Tranches', {
            'fields': ('first_tranche', 'second_tranche', 'third_tranche', 'dost_viii')
        }),
        ('Timeline', {
            'fields': ('project_start', 'project_end', 'original_project_duration', 'extension_date', 'date_of_completion', 'date_of_release')
        }),
        ('Liquidation & Reports', {
            'fields': ('status_of_liquidation', 'date_of_liquidation', 'amount_liquidated', 'tafr', 'par', 'terminal_report', 'invoice_receipt')
        }),
        ('Equipment & Donation', {
            'fields': ('list_of_eqpt', 'donated', 'date_of_donation', 'donation_status', 'date_of_inspection_tagging', 'acknowledgment_receipt_by_grantee')
        }),
        ('Interventions', {
            'fields': ('interventions', 'availed_technologies', 'pme_visit', 'womens_group', 'product_photo')
        }),
        ('Legacy/System Fields', {
            'description': 'Fields used by system logic/relationships',
            'fields': ('proposal', 'budget', 'project_leader', 'approved_budget', 'supporting_documents', 'short_duration_notified', 'date_created', 'date_updated')
        }),
    )


# ------------------------
# Project Expense Admin
# ------------------------
@admin.register(ProjectExpense)
class ProjectExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_title', 'project', 'expense_amount', 'expense_date', 'uploaded_by')
    search_fields = ('expense_title', 'project__project_title')
    list_filter = ('expense_date',)
    readonly_fields = ('date_created',)
    fieldsets = (
        ('Expense Details', {
            'fields': ('project', 'expense_title', 'expense_amount', 'expense_date', 'receipt_document', 'remarks')
        }),
        ('Uploader Information', {
            'fields': ('uploaded_by', 'date_created')
        }),
    )


# ------------------------
# Budget Transaction Admin
# ------------------------
@admin.register(BudgetTransaction)
class BudgetTransactionAdmin(admin.ModelAdmin):
    list_display = ('budget', 'transaction_type', 'amount', 'project', 'processed_by', 'date_transaction')
    list_filter = ('transaction_type', 'date_transaction')
    search_fields = ('budget__fund_source', 'project__project_title', 'processed_by__username')
    readonly_fields = ('date_transaction',)
    fieldsets = (
        ('Transaction Info', {
            'fields': ('budget', 'project', 'transaction_type', 'amount', 'description')
        }),
        ('Processed By', {
            'fields': ('processed_by', 'date_transaction')
        }),
    )


# ------------------------
# Approval Log Admin
# ------------------------
@admin.register(ApprovalLog)
class ApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'action', 'reviewed_by', 'date')
    list_filter = ('action', 'date')
    search_fields = ('proposal__title', 'reviewed_by__username')
    readonly_fields = ('date',)
    fieldsets = (
        ('Approval Details', {
            'fields': ('proposal', 'reviewed_by', 'action', 'remarks')
        }),
        ('Timestamps', {
            'fields': ('date',)
        }),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'due_date', 'completion_date', 'latitude', 'longitude', 'location_name', 'due_date_notified')
    list_filter = ('status', 'project', 'assigned_to')
    search_fields = ('title', 'description', 'project__project_title', 'assigned_to__username')
    ordering = ('-due_date',)
    autocomplete_fields = ['project', 'assigned_to']
    list_per_page = 20

    fieldsets = (
        ('Task Information', {
            'fields': ('project', 'title', 'description', 'assigned_to', 'location_name', 'due_date_notified')
        }),
        ('Schedule', {
            'fields': ('due_date', 'completion_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Location (GIS Mapping)', {
            'fields': ('latitude', 'longitude')
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'message', 'status', 'timestamp')
    list_filter = ('status', 'timestamp', 'receiver')
    search_fields = ('message', 'sender__username', 'receiver__username')
    ordering = ('-timestamp',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'reason_preview', 'ip_address', 'timestamp')
    list_filter = ('action', 'model_name', 'timestamp', 'user')
    search_fields = ('model_name', 'object_id', 'user__username', 'user__email', 'reason')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'old_data', 'new_data', 'reason', 'ip_address', 'timestamp')

    fieldsets = (
        ('Audit Information', {
            'fields': ('user', 'action', 'model_name', 'object_id', 'ip_address')
        }),
        ('Justification', {
            'fields': ('reason',),
            'description': 'Reason/justification for this action'
        }),
        ('Data Changes', {
            'fields': ('old_data', 'new_data')
        }),
        ('Timestamps', {
            'fields': ('timestamp',)
        }),
    )
    
    def reason_preview(self, obj):
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return '-'
    reason_preview.short_description = 'Reason'


# ------------------------
# Document Model Admins
# ------------------------
# Equipment & DOST Compliance Admins
# ------------------------
@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(EquipmentItem)
class EquipmentItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'estimated_unit_cost', 'specifications')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'description', 'specifications')
    fieldsets = (
        ('Equipment Details', {
            'fields': ('name', 'description', 'category')
        }),
        ('Specifications', {
            'fields': ('unit', 'estimated_unit_cost', 'specifications')
        }),
    )


@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = ('budget', 'equipment_item', 'allocated_quantity', 'delivered_quantity', 'status', 'allocation_date')
    list_filter = ('status', 'budget__fiscal_year', 'budget__fund_source')
    search_fields = ('budget__fund_source', 'equipment_item__name')
    readonly_fields = ('date_created', 'date_updated')


@admin.register(ProjectEquipment)
class ProjectEquipmentAdmin(admin.ModelAdmin):
    list_display = ('project', 'get_equipment_name', 'delivered_quantity', 'status', 'property_tag_number', 'ownership_status', 'delivery_date')
    list_filter = ('status', 'ownership_status', 'delivery_date')
    search_fields = ('project__project_title', 'property_tag_number', 'serial_numbers')
    readonly_fields = ('date_created', 'ownership_end_date', 'days_until_ownership', 'ownership_progress_percentage', 'is_eligible_for_transfer')
    
    fieldsets = (
        ('Equipment Delivery', {
            'fields': ('project', 'budget_allocation', 'delivered_quantity', 'delivery_date', 'status')
        }),
        ('Identification', {
            'fields': ('property_tag_number', 'serial_numbers', 'condition_notes')
        }),
        ('Delivery Info', {
            'fields': ('delivered_by', 'received_by')
        }),
        ('DOST SETUP Ownership Tracking', {
            'fields': ('lease_start_date', 'ownership_status', 'ownership_transfer_date'),
            'description': 'Track 3-year equipment ownership timeline for SETUP projects'
        }),
        ('Ownership Calculations (Read-Only)', {
            'fields': ('ownership_end_date', 'days_until_ownership', 'ownership_progress_percentage', 'is_eligible_for_transfer'),
            'classes': ('collapse',)
        }),
    )
    
    def get_equipment_name(self, obj):
        return obj.budget_allocation.equipment_item.name
    get_equipment_name.short_description = 'Equipment'


@admin.register(TrancheRelease)
class TrancheReleaseAdmin(admin.ModelAdmin):
    list_display = ('project', 'tranche_number', 'amount', 'liquidation_status', 'liquidation_percentage_display', 'eligible_for_next_tranche', 'release_date')
    list_filter = ('tranche_number', 'liquidation_status', 'is_released', 'eligible_for_next_tranche')
    search_fields = ('project__project_title', 'check_number', 'bank_account')
    readonly_fields = ('date_created', 'date_updated', 'liquidation_percentage', 'remaining_to_liquidate', 'meets_liquidation_requirement')
    
    fieldsets = (
        ('Tranche Information', {
            'fields': ('project', 'tranche_number', 'amount', 'is_released')
        }),
        ('Release Details', {
            'fields': ('release_date', 'check_number', 'bank_account')
        }),
        ('Liquidation Tracking', {
            'fields': ('liquidation_status', 'liquidation_amount', 'liquidation_date', 'liquidation_document', 'required_liquidation_percentage')
        }),
        ('Eligibility Calculations (Read-Only)', {
            'fields': ('liquidation_percentage', 'remaining_to_liquidate', 'meets_liquidation_requirement', 'eligible_for_next_tranche'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('remarks', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('date_created', 'date_updated')
        }),
    )
    
    def liquidation_percentage_display(self, obj):
        return f"{obj.liquidation_percentage}%"
    liquidation_percentage_display.short_description = 'Liquidated %'


# ------------------------
# Document Model Admins
# ------------------------
@admin.register(BudgetDocument)
class BudgetDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'budget', 'uploaded_by', 'date_uploaded')
    list_filter = ('budget__fiscal_year',)
    search_fields = ('filename', 'budget__fund_source')
    readonly_fields = ('date_uploaded',)


@admin.register(ProposalDocument)
class ProposalDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'proposal', 'uploaded_by', 'date_uploaded')
    search_fields = ('filename', 'proposal__title')
    readonly_fields = ('date_uploaded',)


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'project', 'document_type', 'uploaded_by', 'date_uploaded')
    list_filter = ('document_type',)
    search_fields = ('filename', 'project__project_title')
    readonly_fields = ('date_uploaded',)


@admin.register(ExpenseDocument)
class ExpenseDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'expense', 'uploaded_by', 'date_uploaded')
    search_fields = ('filename', 'expense__expense_title')
    readonly_fields = ('date_uploaded',)


# ------------------------
# Extension Request Admin
# ------------------------
@admin.register(ExtensionRequest)
class ExtensionRequestAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'proponent', 'status', 'date_submitted')
    list_filter = ('status', 'date_submitted')
    search_fields = ('proposal__title', 'proponent__username')


# ------------------------
# Personal Task Admin
# ------------------------
@admin.register(PersonalTask)
class PersonalTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'status', 'priority', 'due_date', 'created_at')
    list_filter = ('status', 'priority', 'due_date', 'created_at')
    search_fields = ('title', 'user__username', 'project__project_title')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Task Information', {
            'fields': ('user', 'project', 'title', 'description', 'checklist')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'due_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


# ------------------------
# Communication Hub Admin
# ------------------------

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'recipient', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'is_archived', 'created_at')
    search_fields = ('subject', 'content', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    fieldsets = (
        ('Message Details', {
            'fields': ('sender', 'recipient', 'subject', 'content', 'message_type')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_archived', 'parent_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(GroupChat)
class GroupChatAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'created_by__username', 'project__project_title')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Group Chat Info', {
            'fields': ('name', 'description', 'project', 'created_by', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(GroupChatMember)
class GroupChatMemberAdmin(admin.ModelAdmin):
    list_display = ('group_chat', 'user', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'joined_at')
    search_fields = ('group_chat__name', 'user__username')
    readonly_fields = ('joined_at',)

@admin.register(GroupChatMessage)
class GroupChatMessageAdmin(admin.ModelAdmin):
    list_display = ('group_chat', 'sender', 'content_preview', 'is_edited', 'created_at')
    list_filter = ('is_edited', 'created_at')
    search_fields = ('group_chat__name', 'sender__username', 'content')
    readonly_fields = ('created_at', 'edited_at')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'created_by', 'is_active', 'expires_at', 'created_at')
    list_filter = ('priority', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Announcement Details', {
            'fields': ('title', 'content', 'priority', 'created_by')
        }),
        ('Settings', {
            'fields': ('is_active', 'expires_at', 'target_roles', 'target_users')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# ------------------------
# System Health Admin
# ------------------------

@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ('metric_type', 'value', 'unit', 'status', 'recorded_at')
    list_filter = ('metric_type', 'status', 'recorded_at')
    readonly_fields = ('recorded_at',)
    fieldsets = (
        ('Metric Information', {
            'fields': ('metric_type', 'value', 'unit', 'status')
        }),
        ('Timestamp', {
            'fields': ('recorded_at',)
        }),
    )

@admin.register(BackupStatus)
class BackupStatusAdmin(admin.ModelAdmin):
    list_display = ('backup_type', 'status', 'file_size_display', 'started_at', 'completed_at', 'initiated_by')
    list_filter = ('backup_type', 'status', 'started_at')
    search_fields = ('initiated_by__username', 'error_message')
    readonly_fields = ('created_at', 'started_at', 'completed_at')
    fieldsets = (
        ('Backup Details', {
            'fields': ('backup_type', 'status', 'file_path', 'file_size')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'created_at')
        }),
        ('User & Error Info', {
            'fields': ('initiated_by', 'error_message')
        }),
    )

    def file_size_display(self, obj):
        if obj.file_size:
            # Convert bytes to human readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024.0:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024.0
            return f"{obj.file_size:.1f} TB"
        return "N/A"
    file_size_display.short_description = 'File Size'

@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ('title', 'maintenance_type', 'status', 'scheduled_at', 'assigned_to', 'is_recurring')
    list_filter = ('maintenance_type', 'status', 'is_recurring', 'scheduled_at')
    search_fields = ('title', 'description', 'assigned_to__username', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')
    fieldsets = (
        ('Maintenance Details', {
            'fields': ('title', 'description', 'maintenance_type', 'status')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'estimated_duration', 'is_recurring', 'recurrence_pattern')
        }),
        ('Assignment & Timing', {
            'fields': ('created_by', 'assigned_to', 'started_at', 'completed_at', 'actual_duration')
        }),
        ('Error Handling', {
            'fields': ('error_message',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
