# core/templatetags/core_filters.py

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adds a CSS class to a form field.
    Usage: {{ field|add_class:"my-class" }}
    """
    return value.as_widget(attrs={'class': arg})

@register.filter(name='add_placeholder')
def add_placeholder(field, text):
    """
    Adds a placeholder attribute to a form field.
    Usage: {{ field|add_placeholder:"Enter your username" }}
    """
    field.field.widget.attrs['placeholder'] = text
    return field

@register.filter(name='is_checkbox')
def is_checkbox(field):
    return field.field.widget.__class__.__name__ == 'CheckboxInput'









# core/templatetags/core_filters.py

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adds a CSS class to a form field.
    Usage: {{ field|add_class:"my-class" }}
    """
    return value.as_widget(attrs={'class': arg})

@register.filter(name='add_placeholder')
def add_placeholder(field, text):
    """
    Adds a placeholder attribute to a form field.
    Usage: {{ field|add_placeholder:"Enter your username" }}
    """
    field.field.widget.attrs['placeholder'] = text
    return field

@register.filter(name='is_checkbox')
def is_checkbox(field):
    return field.field.widget.__class__.__name__ == 'CheckboxInput'

# New custom filter to check if a string starts with a value
@register.filter
def startswith(value, arg):
    """
    Checks if a string starts with a given substring.
    Usage: {{ value|startswith:arg }}
    """
    return value.startswith(arg)