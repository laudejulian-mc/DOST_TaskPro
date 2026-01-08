from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    """Form for sending messages"""
    class Meta:
        model = Message
        fields = ['subject', 'content', 'attachment']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter message subject'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y min-h-[120px]',
                'placeholder': 'Type your message here...',
                'rows': 4
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
            })
        }