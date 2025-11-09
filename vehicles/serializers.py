from rest_framework import serializers
from .models import Brand, VehicleModel, VehicleCategory, VehicleSpecification, VehicleFeature, VehicleSpecificationFeature, FuelType, TransmissionType


class FuelTypeSerializer(serializers.ModelSerializer):
    """Serializer for fuel types."""
    
    class Meta:
        model = FuelType
        fields = ['id', 'name', 'slug', 'description', 'icon', 'is_active']


class TransmissionTypeSerializer(serializers.ModelSerializer):
    """Serializer for transmission types."""
    
    class Meta:
        model = TransmissionType
        fields = ['id', 'name', 'slug', 'description', 'icon', 'is_active']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for vehicle brands."""
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'country_of_origin', 'website', 'founded_year']


class VehicleCategorySerializer(serializers.ModelSerializer):
    """Serializer for vehicle categories."""
    
    class Meta:
        model = VehicleCategory
        fields = ['id', 'name', 'description', 'icon']


class VehicleModelListSerializer(serializers.ModelSerializer):
    """Serializer for listing vehicle models."""
    brand = BrandSerializer(read_only=True)
    category = VehicleCategorySerializer(read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'name', 'brand', 'category', 'image']


class VehicleModelDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vehicle models."""
    brand = BrandSerializer(read_only=True)
    category = VehicleCategorySerializer(read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'name', 'brand', 'category', 'image', 'description', 
                 'launch_year', 'is_active', 'created_at', 'updated_at']


class VehicleFeatureSerializer(serializers.ModelSerializer):
    """Serializer for vehicle features."""
    
    class Meta:
        model = VehicleFeature
        fields = ['id', 'name', 'description', 'category', 'icon']


class VehicleSpecificationFeatureSerializer(serializers.ModelSerializer):
    """Serializer for vehicle specification features."""
    feature = VehicleFeatureSerializer(read_only=True)
    
    class Meta:
        model = VehicleSpecificationFeature
        fields = ['feature', 'is_standard', 'is_optional', 'details']


class VehicleSpecificationListSerializer(serializers.ModelSerializer):
    """Serializer for listing vehicle specifications."""
    model = VehicleModelListSerializer(read_only=True)
    
    class Meta:
        model = VehicleSpecification
        fields = ['id', 'model', 'year', 'engine_type', 'fuel_type']


class VehicleSpecificationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vehicle specifications."""
    model = VehicleModelDetailSerializer(read_only=True)
    features = VehicleSpecificationFeatureSerializer(source='features', many=True, read_only=True)
    transmission = TransmissionTypeSerializer(read_only=True)
    fuel_type = FuelTypeSerializer(read_only=True)
    
    class Meta:
        model = VehicleSpecification
        fields = [
            'id', 'model', 'year', 'category', 
            'engine_type', 'engine_capacity', 'transmission', 'fuel_type',
            'horsepower', 'torque', 'drive_type', 'acceleration', 'top_speed',
            'fuel_economy', 'body_style', 'doors', 'seating_capacity',
            'length', 'width', 'height', 'wheelbase', 'ground_clearance',
            'trunk_capacity', 'fuel_tank_capacity', 'weight', 'features', 'created_at', 'updated_at'
        ]


class VehicleModelCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating vehicle models."""
    
    class Meta:
        model = VehicleModel
        fields = ['name', 'brand', 'category', 'image', 'description', 'launch_year', 'is_active']


class VehicleSpecificationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating vehicle specifications."""
    features = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    
    class Meta:
        model = VehicleSpecification
        fields = [
            'model', 'year', 'category',
            'engine_type', 'engine_capacity', 'transmission', 'fuel_type',
            'horsepower', 'torque', 'drive_type', 'acceleration', 'top_speed',
            'fuel_economy', 'body_style', 'doors', 'seating_capacity',
            'length', 'width', 'height', 'wheelbase', 'ground_clearance',
            'trunk_capacity', 'fuel_tank_capacity', 'weight', 'features'
        ]
    
    def create(self, validated_data):
        features_data = validated_data.pop('features', [])
        specification = VehicleSpecification.objects.create(**validated_data)
        
        # Create specification features
        self._process_features(specification, features_data)
        
        return specification
    
    def update(self, instance, validated_data):
        features_data = validated_data.pop('features', [])
        
        # Update specification fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update specification features if provided
        if features_data:
            # Clear existing features
            instance.vehiclespecificationfeature_set.all().delete()
            # Create new features
            self._process_features(instance, features_data)
        
        return instance
    
    def _process_features(self, specification, features_data):
        for feature_data in features_data:
            feature_id = feature_data.get('feature_id')
            if feature_id:
                try:
                    feature = VehicleFeature.objects.get(id=feature_id)
                    VehicleSpecificationFeature.objects.create(
                        specification=specification,
                        feature=feature,
                        is_standard=feature_data.get('is_standard', False),
                        is_optional=feature_data.get('is_optional', False),
                        details=feature_data.get('details', '')
                    )
                except VehicleFeature.DoesNotExist:
                    pass  # Skip if feature doesn't exist