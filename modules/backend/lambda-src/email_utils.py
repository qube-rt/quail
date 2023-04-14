import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape, StrictUndefined


def render_template(template_name, template_data, template_path="./templates"):
    env = Environment(
        loader=FileSystemLoader(searchpath=template_path),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
    )

    text = env.get_template(f"{template_name}.txt").render(**template_data)
    html = env.get_template(f"{template_name}.html").render(**template_data)

    return text, html


def send_email(subject, template_name, template_data, source_email, to_email, cc_email=None):
    rendered_text, rendered_html = render_template(template_name=template_name, template_data=template_data)

    extra_destination = {}
    if cc_email:
        extra_destination["CcAddresses"] = [cc_email]
    ses_client = boto3.client("ses")
    response = ses_client.send_email(
        Source=source_email,
        Destination={
            "ToAddresses": [
                to_email,
            ],
            **extra_destination,
        },
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": rendered_text},
                "Html": {"Data": rendered_html},
            },
        },
    )

    return response
