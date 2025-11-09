from rest_framework import serializers


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            # Drop fields that are specified in the `exclude` argument
            for field_name in exclude:
                if field_name in self.fields:
                    self.fields.pop(field_name)


class ReadWriteSerializerMethodField(serializers.SerializerMethodField):
    """A SerializerMethodField that can be used for both read and write operations."""

    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        super(serializers.SerializerMethodField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        # The field is read-only, so we just return the data as is
        return {self.field_name: data}


class RecursiveField(serializers.Serializer):
    """A field that can be used to represent a recursive relationship."""

    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class TimestampField(serializers.Field):
    """A field that converts a datetime to a timestamp and vice versa."""

    def to_representation(self, value):
        import calendar
        import datetime

        if value is None:
            return None

        if isinstance(value, (int, float)):
            return value

        if isinstance(value, datetime.datetime):
            return calendar.timegm(value.utctimetuple())

        return None

    def to_internal_value(self, value):
        import datetime

        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError(
                'Timestamp value must be a number.'
            )

        return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)