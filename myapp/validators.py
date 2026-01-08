"""
Custom validators for the DOST Project Management System.
Provides validation for forms, files, and input data.
"""

import os
import re
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, InvalidOperation


# ============================================
# FILE UPLOAD VALIDATORS
# ============================================

# Allowed file types for different upload categories
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
ALLOWED_ALL_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS + ALLOWED_IMAGE_EXTENSIONS

# Maximum file sizes (in bytes)
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PROFILE_PICTURE_SIZE = 2 * 1024 * 1024  # 2 MB


def validate_file_extension(file, allowed_extensions=None):
    """
    Validate that the uploaded file has an allowed extension.
    
    Args:
        file: The uploaded file object
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])
    
    Raises:
        ValidationError: If file extension is not allowed
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_ALL_EXTENSIONS
    
    if file:
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f'File type "{ext}" is not allowed. Allowed types: {", ".join(allowed_extensions)}'
            )


def validate_file_size(file, max_size=MAX_DOCUMENT_SIZE):
    """
    Validate that the uploaded file doesn't exceed the maximum size.
    
    Args:
        file: The uploaded file object
        max_size: Maximum file size in bytes
    
    Raises:
        ValidationError: If file size exceeds maximum
    """
    if file:
        if file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            file_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f'File size ({file_mb:.2f} MB) exceeds maximum allowed size ({max_mb:.2f} MB).'
            )


def validate_document_upload(file):
    """
    Validate a document upload (PDF, Word, Excel, etc.).
    
    Args:
        file: The uploaded file object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_extension(file, ALLOWED_DOCUMENT_EXTENSIONS)
    validate_file_size(file, MAX_DOCUMENT_SIZE)


def validate_image_upload(file):
    """
    Validate an image upload (JPG, PNG, etc.).
    
    Args:
        file: The uploaded file object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_extension(file, ALLOWED_IMAGE_EXTENSIONS)
    validate_file_size(file, MAX_IMAGE_SIZE)


def validate_profile_picture(file):
    """
    Validate a profile picture upload with stricter size limits.
    
    Args:
        file: The uploaded file object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_extension(file, ALLOWED_IMAGE_EXTENSIONS)
    validate_file_size(file, MAX_PROFILE_PICTURE_SIZE)


# ============================================
# INPUT VALIDATION HELPERS
# ============================================

def sanitize_string(value, max_length=None, allow_empty=False):
    """
    Sanitize and validate a string input.
    
    Args:
        value: The input string
        max_length: Maximum allowed length
        allow_empty: Whether empty strings are allowed
    
    Returns:
        Sanitized string
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        value = ''
    
    # Strip whitespace
    value = str(value).strip()
    
    if not allow_empty and not value:
        raise ValidationError(_('This field cannot be empty.'), code='empty_field')
    
    if max_length and len(value) > max_length:
        raise ValidationError(
            _('Value exceeds maximum length of %(max)d characters.'),
            params={'max': max_length},
            code='max_length_exceeded'
        )
    
    return value


def validate_email(email):
    """
    Validate an email address.
    
    Args:
        email: The email string to validate
    
    Returns:
        Validated email string
    
    Raises:
        ValidationError: If email is invalid
    """
    email = sanitize_string(email)
    validator = EmailValidator()
    validator(email)
    return email.lower()


def validate_phone_number(phone):
    """
    Validate a Philippine phone number.
    
    Args:
        phone: The phone number string
    
    Returns:
        Validated phone number
    
    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone:
        return None
    
    # Remove spaces, dashes, and parentheses
    phone = re.sub(r'[\s\-\(\)]+', '', phone)
    
    # Philippine mobile: 09XXXXXXXXX or +639XXXXXXXXX
    # Philippine landline: (area code) XXX-XXXX
    mobile_pattern = r'^(\+63|0)?9\d{9}$'
    landline_pattern = r'^(\+63|0)?[2-8]\d{7,9}$'
    
    if not (re.match(mobile_pattern, phone) or re.match(landline_pattern, phone)):
        raise ValidationError(
            _('Invalid phone number format. Use formats like 09XXXXXXXXX or +639XXXXXXXXX.'),
            code='invalid_phone'
        )
    
    return phone


def validate_positive_decimal(value, field_name='Amount', max_digits=15, decimal_places=2):
    """
    Validate that a value is a positive decimal number.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        max_digits: Maximum total digits
        decimal_places: Maximum decimal places
    
    Returns:
        Validated Decimal value
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None or value == '':
        return Decimal('0.00')
    
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(f'{field_name} must be a valid number.')
    
    if decimal_value < 0:
        raise ValidationError(f'{field_name} cannot be negative.')
    
    # Check precision
    sign, digits, exponent = decimal_value.as_tuple()
    total_digits = len(digits)
    decimal_digits = -exponent if exponent < 0 else 0
    
    if decimal_digits > decimal_places:
        raise ValidationError(f'{field_name} cannot have more than {decimal_places} decimal places.')
    
    if total_digits > max_digits:
        raise ValidationError(f'{field_name} cannot have more than {max_digits} digits.')
    
    return decimal_value


def validate_positive_integer(value, field_name='Value', min_value=0, max_value=None):
    """
    Validate that a value is a positive integer.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Validated integer value
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None or value == '':
        return 0
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(
            _('%(field)s must be a valid integer.'),
            params={'field': field_name},
            code='invalid_integer'
        )
    
    if int_value < min_value:
        raise ValidationError(
            _('%(field)s must be at least %(min)d.'),
            params={'field': field_name, 'min': min_value},
            code='below_minimum'
        )
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(
            _('%(field)s cannot exceed %(max)d.'),
            params={'field': field_name, 'max': max_value},
            code='above_maximum'
        )
    
    return int_value


def validate_password_strength(password, min_length=8):
    """
    Validate password meets minimum security requirements.
    
    Args:
        password: The password string
        min_length: Minimum password length
    
    Returns:
        Validated password
    
    Raises:
        ValidationError: If password is too weak
    """
    if not password:
        raise ValidationError('Password is required.')
    
    if len(password) < min_length:
        raise ValidationError(f'Password must be at least {min_length} characters long.')
    
    # Check for at least one letter and one number
    if not re.search(r'[A-Za-z]', password):
        raise ValidationError('Password must contain at least one letter.')
    
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number.')
    
    return password


def validate_date_range(start_date, end_date, field_names=('Start date', 'End date')):
    """
    Validate that start_date is before or equal to end_date.
    
    Args:
        start_date: The start date
        end_date: The end date
        field_names: Tuple of field names for error messages
    
    Raises:
        ValidationError: If date range is invalid
    """
    if start_date and end_date and start_date > end_date:
        raise ValidationError(
            _('%(start)s cannot be after %(end)s.'),
            params={'start': field_names[0], 'end': field_names[1]},
            code='invalid_date_range'
        )


# ============================================
# FORM DATA VALIDATION HELPERS
# ============================================

def validate_user_form_data(data, is_edit=False):
    """
    Validate user creation/edit form data.
    
    Args:
        data: Dictionary of form data
        is_edit: Whether this is an edit operation
    
    Returns:
        Dictionary of validated data
    
    Raises:
        ValidationError: If validation fails
    """
    validated = {}
    errors = []
    
    try:
        validated['email'] = validate_email(data.get('email', ''))
    except ValidationError as e:
        errors.append(f"Email: {e.message}")
    
    try:
        validated['first_name'] = sanitize_string(data.get('first_name', ''), max_length=50, allow_empty=True)
    except ValidationError as e:
        errors.append(f"First Name: {e.message}")
    
    try:
        validated['last_name'] = sanitize_string(data.get('last_name', ''), max_length=50, allow_empty=True)
    except ValidationError as e:
        errors.append(f"Last Name: {e.message}")
    
    if data.get('contact_number'):
        try:
            validated['contact_number'] = validate_phone_number(data.get('contact_number'))
        except ValidationError as e:
            errors.append(f"Contact Number: {e.message}")
    
    if not is_edit and data.get('password'):
        try:
            validated['password'] = validate_password_strength(data.get('password'))
        except ValidationError as e:
            errors.append(f"Password: {e.message}")
        
        if data.get('password') != data.get('confirm_password'):
            errors.append("Passwords do not match.")
    
    if errors:
        raise ValidationError(errors)
    
    return validated


def validate_proposal_form_data(data):
    """
    Validate proposal form data.
    
    Args:
        data: Dictionary of form data
    
    Returns:
        Dictionary of validated data
    
    Raises:
        ValidationError: If validation fails
    """
    validated = {}
    errors = []
    
    try:
        validated['title'] = sanitize_string(data.get('title', ''), max_length=255)
    except ValidationError as e:
        errors.append(f"Title: {e.message}")
    
    try:
        validated['proposed_amount'] = validate_positive_decimal(
            data.get('proposed_amount', 0),
            field_name='Proposed Amount'
        )
    except ValidationError as e:
        errors.append(f"Proposed Amount: {e.message}")
    
    validated['description'] = data.get('description', '')
    validated['location'] = data.get('location', '')
    
    if errors:
        raise ValidationError(errors)
    
    return validated


def validate_project_form_data(data):
    """
    Validate project form data.
    
    Args:
        data: Dictionary of form data
    
    Returns:
        Dictionary of validated data
    
    Raises:
        ValidationError: If validation fails
    """
    validated = {}
    errors = []
    
    try:
        validated['project_title'] = sanitize_string(data.get('project_title', ''), max_length=255)
    except ValidationError as e:
        errors.append(f"Project Title: {e.message}")
    
    try:
        validated['funds'] = validate_positive_decimal(
            data.get('funds', 0),
            field_name='Funds'
        )
    except ValidationError as e:
        errors.append(f"Funds: {e.message}")
    
    try:
        validated['no_of_beneficiaries'] = validate_positive_integer(
            data.get('no_of_beneficiaries', 0),
            field_name='Number of Beneficiaries'
        )
    except ValidationError as e:
        errors.append(f"Number of Beneficiaries: {e.message}")
    
    if errors:
        raise ValidationError(errors)
    
    return validated
