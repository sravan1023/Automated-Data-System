"""
AutoDocs AI - Template Engine Service

Renders templates with Jinja2 and converts to various formats.
"""
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError
from typing import Optional
import re


# Custom Jinja2 environment
_jinja_env = Environment(
    loader=BaseLoader(),
    autoescape=True,
)


# Add custom filters
def currency_filter(value, symbol="$", decimals=2):
    """Format number as currency."""
    try:
        num = float(value)
        return f"{symbol}{num:,.{decimals}f}"
    except (ValueError, TypeError):
        return value


def date_filter(value, format="%B %d, %Y"):
    """Format date string."""
    from dateutil.parser import parse
    try:
        dt = parse(str(value))
        return dt.strftime(format)
    except:
        return value


def uppercase_filter(value):
    """Convert to uppercase."""
    return str(value).upper()


def lowercase_filter(value):
    """Convert to lowercase."""
    return str(value).lower()


def titlecase_filter(value):
    """Convert to title case."""
    return str(value).title()


def default_filter(value, default_value=""):
    """Return default if value is None or empty."""
    if value is None or value == "":
        return default_value
    return value


# Register filters
_jinja_env.filters["currency"] = currency_filter
_jinja_env.filters["date"] = date_filter
_jinja_env.filters["upper"] = uppercase_filter
_jinja_env.filters["lower"] = lowercase_filter
_jinja_env.filters["title"] = titlecase_filter
_jinja_env.filters["default"] = default_filter


def render_template(
    template_content: str,
    css_content: str,
    data: dict,
) -> str:
    """
    Render template with data.
    
    Args:
        template_content: HTML template with Jinja2 syntax
        css_content: CSS styles
        data: Data dict for template variables
    
    Returns:
        Rendered HTML string
    """
    try:
        template = _jinja_env.from_string(template_content)
        body_html = template.render(**data)
        
        # Wrap with full HTML document
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        {css_content or ''}
        
        /* Default styles */
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f4f4f4;
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
        
        return full_html
    
    except TemplateSyntaxError as e:
        raise ValueError(f"Template syntax error: {e.message} (line {e.lineno})")
    
    except UndefinedError as e:
        raise ValueError(f"Missing variable: {e.message}")


def validate_template(template_content: str) -> tuple[bool, Optional[str]]:
    """
    Validate template syntax.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        _jinja_env.from_string(template_content)
        return True, None
    except TemplateSyntaxError as e:
        return False, f"Syntax error: {e.message} (line {e.lineno})"


def extract_variables(template_content: str) -> list[str]:
    """
    Extract variable names from template.
    
    Returns list of variable names used in template.
    """
    # Simple regex to find {{ variable }} patterns
    # This doesn't handle all Jinja2 syntax but covers common cases
    pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)"
    matches = re.findall(pattern, template_content)
    
    # Also find variables in for loops and if statements
    loop_pattern = r"\{%\s*for\s+\w+\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    matches.extend(re.findall(loop_pattern, template_content))
    
    if_pattern = r"\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    matches.extend(re.findall(if_pattern, template_content))
    
    # Remove duplicates and built-in variables
    builtins = {"loop", "range", "true", "false", "none"}
    variables = list(set(matches) - builtins)
    
    return sorted(variables)


def apply_mapping(
    row_data: dict,
    mapping: dict[str, str],
) -> dict:
    """
    Apply field mapping to row data.
    
    Args:
        row_data: Original row data {datasource_column: value}
        mapping: Mapping {template_var: datasource_column}
    
    Returns:
        Mapped data {template_var: value}
    """
    mapped_data = {}
    
    for template_var, datasource_col in mapping.items():
        if datasource_col in row_data:
            mapped_data[template_var] = row_data[datasource_col]
        else:
            mapped_data[template_var] = None
    
    return mapped_data


# Sample templates for testing
SAMPLE_TEMPLATES = {
    "invoice": """
<div class="invoice">
    <h1>INVOICE</h1>
    <div class="header">
        <p><strong>Invoice #:</strong> {{invoice_number}}</p>
        <p><strong>Date:</strong> {{invoice_date | date}}</p>
    </div>
    
    <div class="client">
        <h2>Bill To:</h2>
        <p>{{client_name | title}}</p>
        <p>{{client_address}}</p>
        <p>{{client_email}}</p>
    </div>
    
    <table class="items">
        <thead>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for item in line_items %}
            <tr>
                <td>{{item.description}}</td>
                <td>{{item.quantity}}</td>
                <td>{{item.unit_price | currency}}</td>
                <td>{{item.amount | currency}}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="totals">
        <p><strong>Subtotal:</strong> {{subtotal | currency}}</p>
        {% if tax %}
        <p><strong>Tax:</strong> {{tax | currency}}</p>
        {% endif %}
        <p class="total"><strong>Total:</strong> {{total | currency}}</p>
    </div>
</div>
""",
    
    "letter": """
<div class="letter">
    <p class="date">{{date | date}}</p>
    
    <div class="recipient">
        <p>{{recipient_name | title}}</p>
        <p>{{recipient_address}}</p>
        <p>{{recipient_city}}, {{recipient_state}} {{recipient_zip}}</p>
    </div>
    
    <p class="greeting">Dear {{recipient_name | title}},</p>
    
    <div class="body">
        {{body_content}}
    </div>
    
    <div class="signature">
        <p>Sincerely,</p>
        <p>{{sender_name}}</p>
        <p>{{sender_title}}</p>
    </div>
</div>
""",
    
    "certificate": """
<div class="certificate">
    <h1>Certificate of Completion</h1>
    <p class="subtitle">This is to certify that</p>
    <h2 class="name">{{recipient_name | title}}</h2>
    <p>has successfully completed</p>
    <h3 class="course">{{course_name}}</h3>
    <p>on {{completion_date | date}}</p>
    
    <div class="signature">
        <p>{{issuer_name}}</p>
        <p>{{issuer_title}}</p>
    </div>
</div>
""",
}
