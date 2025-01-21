from django import template

register = template.Library()

@register.filter(name='format_status')
def format_status(value):
    if value == 'pending':
        return 'Chờ xét duyệt'
    if value == 'verified':
        return 'Cv đã duyệt'
    if value == 'accepted':
        return 'Admin đã duyệt'
    if value == 'rejected':
        return 'Admin đã từ chối'
    return value.capitalize()
