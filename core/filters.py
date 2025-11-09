from django_filters import rest_framework as filters
from django.db.models import Q


class MultipleValueFilter(filters.BaseCSVFilter, filters.CharFilter):
    """Filter that allows for multiple values for a single field."""
    
    def filter(self, qs, value):
        if not value:
            return qs
        
        # Split the value by comma and filter by each value
        values = value.split(',') if isinstance(value, str) else value
        lookup = f'{self.field_name}__{self.lookup_expr}'
        
        # Create a Q object for each value and combine them with OR
        q_objects = Q()
        for val in values:
            q_objects |= Q(**{lookup: val})
        
        return qs.filter(q_objects).distinct()


class MultipleChoiceFilter(filters.BaseInFilter, filters.CharFilter):
    """Filter that allows for multiple choices for a single field."""
    pass