from rest_framework.response import Response
from rest_framework import status


class MultiSerializerViewSetMixin:
    """Mixin that allows a viewset to use different serializers for different actions."""
    serializer_classes = {}
    
    def get_serializer_class(self):
        """Return the serializer class for the current action."""
        return self.serializer_classes.get(self.action, super().get_serializer_class())


class OwnerFilterViewSetMixin:
    """Mixin that filters queryset to only include objects owned by the current user."""
    owner_field = 'user'
    
    def get_queryset(self):
        """Filter queryset to only include objects owned by the current user."""
        queryset = super().get_queryset()
        
        # If user is staff, return all objects
        if self.request.user.is_staff:
            return queryset
        
        # Otherwise, filter by owner
        return queryset.filter(**{self.owner_field: self.request.user})


class CreateWithOwnerMixin:
    """Mixin that automatically sets the owner of a new object to the current user."""
    owner_field = 'user'
    
    def perform_create(self, serializer):
        """Set the owner of the new object to the current user."""
        serializer.save(**{self.owner_field: self.request.user})


class SuccessMessageMixin:
    """Mixin that adds a success message to the response."""
    success_message = ''
    
    def get_success_message(self, serializer):
        """Return the success message."""
        return self.success_message
    
    def create(self, request, *args, **kwargs):
        """Add success message to create response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        response_data = serializer.data
        message = self.get_success_message(serializer)
        if message:
            response_data = {
                'message': message,
                'data': serializer.data
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Add success message to update response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        response_data = serializer.data
        message = self.get_success_message(serializer)
        if message:
            response_data = {
                'message': message,
                'data': serializer.data
            }
        
        return Response(response_data)