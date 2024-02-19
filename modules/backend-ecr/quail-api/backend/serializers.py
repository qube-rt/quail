from datetime import datetime, timedelta, timezone

from marshmallow import Schema, fields, EXCLUDE, validates_schema, ValidationError
from marshmallow.validate import OneOf, Range, Length, Equal


def group_serializer(groups):
    class GroupSchema(Schema):
        group = fields.Str(required=True, validate=OneOf(groups))

        class Meta:
            unknown = EXCLUDE

    return GroupSchema()


def instance_post_serializer(
    accounts,
    region_map,
    instance_types,
    max_days_to_expiry,
    initiator_username,
    initator_email,
    is_superuser,
):
    min_date = datetime.now(timezone.utc) + timedelta(hours=2)
    max_date = datetime.now(timezone.utc) + timedelta(days=max_days_to_expiry)

    def validate_equal_or_superuser(value):
        return lambda _: True if is_superuser else Equal(value)

    class RequestValidator(Schema):
        account = fields.Str(required=True, validate=OneOf(accounts))
        region = fields.Str(required=True)
        instance_type = fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types))
        operating_system = fields.Str(
            required=True,
            data_key="operatingSystem",
        )
        instance_name = fields.Str(required=True, data_key="instanceName", validate=Length(max=255))
        expiry = fields.AwareDateTime(
            required=True,
            validate=Range(
                min=min_date,
                max=max_date,
                error=(
                    f"Must be between {min_date.strftime('%Y-%m-%d %H:%M')} "
                    f"and {max_date.strftime('%Y-%m-%d %H:%M')}."
                ),
            ),
        )
        email = fields.Email(required=True, validate=validate_equal_or_superuser(initator_email))
        username = fields.Str(required=True, validate=validate_equal_or_superuser(initiator_username))

        @validates_schema
        def validate_lower_bound(self, data, **kwargs):
            # Validate region
            supported_regions = region_map.get(data["account"])

            if not supported_regions or data["region"] not in supported_regions:
                raise ValidationError(f"Missing permission for region {data['region']}.")

            # Validate operating system
            supported_oses = region_map[data["account"]][data["region"]]["os_types"]
            if not supported_oses or data["operating_system"] not in supported_oses:
                raise ValidationError(f"Missing permission for operating_system {data['operating_system']}.")

        class Meta:
            unknown = EXCLUDE

    return RequestValidator()


def instance_patch_serializer(instance_types):
    return Schema.from_dict(
        dict(
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
        )
    )(unknown=EXCLUDE)


class WaitRequestValidator(Schema):
    stackset_id = fields.Str(required=True)
    operation_id = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE


class WaitForUpdateCompletionRequestValidator(Schema):
    stackset_id = fields.Str(required=True)
    update_level = fields.Str(required=True)
    operation_id = fields.Str(required=False, allow_none=True)

    class Meta:
        unknown = EXCLUDE
