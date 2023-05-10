from datetime import datetime, timedelta, timezone

from marshmallow import Schema, fields, EXCLUDE
from marshmallow.validate import OneOf, Range, Length


def instance_post_serializer(
    current_account_id,
    regions,
    instance_types,
    operating_systems,
    max_days_to_expiry,
    is_superuser,
):
    extra_fields = dict()
    if is_superuser:
        extra_fields = dict(
            email=fields.Email(required=True),
            username=fields.Str(required=True),
        )

    min_date = datetime.now(timezone.utc) + timedelta(hours=2)
    max_date = datetime.now(timezone.utc) + timedelta(days=max_days_to_expiry)
    return Schema.from_dict(
        dict(
            account=fields.Constant(constant=current_account_id),
            region=fields.Str(required=True, validate=OneOf(regions)),
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
            operating_system=fields.Str(
                required=True,
                data_key="operatingSystem",
                validate=OneOf(operating_systems),
            ),
            instance_name=fields.Str(required=True, data_key="instanceName", validate=Length(max=255)),
            expiry=fields.AwareDateTime(
                required=True,
                validate=Range(
                    min=min_date,
                    max=max_date,
                    error=(
                        f"Must be between {min_date.strftime('%Y-%m-%d %H:%M')} "
                        f"and {max_date.strftime('%Y-%m-%d %H:%M')}."
                    ),
                ),
            ),
            **extra_fields,
        )
    )(unknown=EXCLUDE)


def instance_patch_serializer(instance_types):
    return Schema.from_dict(
        dict(
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
        )
    )(unknown=EXCLUDE)
