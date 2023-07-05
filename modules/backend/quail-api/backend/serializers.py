from datetime import datetime, timedelta, timezone

from marshmallow import Schema, fields, EXCLUDE, validates_schema, ValidationError
from marshmallow.validate import OneOf, Range, Length, Equal


def instance_post_serializer(
    accounts,
    region_map,
    instance_types,
    max_days_to_expiry,
    initiatorUsername,
    initatorEmail,
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
        email = fields.Email(required=True, validate=validate_equal_or_superuser(initatorEmail))
        username = fields.Str(required=True, validate=validate_equal_or_superuser(initiatorUsername))

        @validates_schema
        def validate_lower_bound(self, data, **kwargs):
            # Validate region
            supported_regions = region_map.get(data["account"])

            if not supported_regions or data["region"] not in supported_regions:
                raise ValidationError(f"Missing permission for region {data['region']}.")

            # Validate operating system
            supported_oses = region_map[data["account"]][data["region"]]
            if not supported_oses or data["operating_system"] not in supported_oses:
                raise ValidationError(f"Missing permission for operating_system {data['operating_system']}.")

        class Meta:
            unknown = EXCLUDE

    return RequestValidator()
    # return Schema.from_dict(
    #     dict(
    #         account=fields.Str(required=True, validate=OneOf(accounts)),
    #         region=fields.Str(required=True, validate=OneOf(regions)),
    #         instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
    #         operating_system=fields.Str(
    #             required=True,
    #             data_key="operatingSystem",
    #             validate=OneOf(operating_systems),
    #         ),
    #         instance_name=fields.Str(required=True, data_key="instanceName", validate=Length(max=255)),
    #         expiry=fields.AwareDateTime(
    #             required=True,
    #             validate=Range(
    #                 min=min_date,
    #                 max=max_date,
    #                 error=(
    #                     f"Must be between {min_date.strftime('%Y-%m-%d %H:%M')} "
    #                     f"and {max_date.strftime('%Y-%m-%d %H:%M')}."
    #                 ),
    #             ),
    #         ),
    #         **extra_fields,
    #     )
    # )(unknown=EXCLUDE)


def instance_patch_serializer(instance_types):
    return Schema.from_dict(
        dict(
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
        )
    )(unknown=EXCLUDE)
