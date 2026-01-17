"""
AutoDocs AI - File Parser Service

Parses CSV, XLSX, and JSON files into normalized data.
"""
import pandas as pd
import json
from io import BytesIO
from typing import Any, Optional
from datetime import datetime

from server.models.datasource import FileType


def parse_file(
    content: bytes,
    file_type: FileType,
) -> tuple[list[dict], dict]:
    """
    Parse file content into rows and schema.
    
    Args:
        content: File bytes
        file_type: Type of file
    
    Returns:
        Tuple of (rows as list of dicts, inferred schema)
    """
    if file_type == FileType.CSV:
        df = parse_csv(content)
    elif file_type == FileType.XLSX:
        df = parse_xlsx(content)
    elif file_type == FileType.JSON:
        df = parse_json(content)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    
    # Normalize column names
    df.columns = [normalize_column_name(col) for col in df.columns]
    
    # Infer schema
    schema = infer_schema(df)
    
    # Convert to list of dicts
    rows = df.to_dict(orient="records")
    
    # Clean values for JSON serialization
    rows = [clean_row(row) for row in rows]
    
    return rows, schema


def parse_csv(content: bytes) -> pd.DataFrame:
    """Parse CSV file."""
    return pd.read_csv(
        BytesIO(content),
        encoding="utf-8",
        on_bad_lines="skip",
    )


def parse_xlsx(content: bytes) -> pd.DataFrame:
    """Parse Excel file (first sheet)."""
    return pd.read_excel(
        BytesIO(content),
        engine="openpyxl",
    )


def parse_json(content: bytes) -> pd.DataFrame:
    """Parse JSON file (array of objects)."""
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict) and "data" in data:
        return pd.DataFrame(data["data"])
    else:
        raise ValueError("JSON must be array or object with 'data' array")


def normalize_column_name(name: str) -> str:
    """
    Normalize column name for consistent access.
    
    - Lowercase
    - Replace spaces with underscores
    - Remove special characters
    """
    import re
    name = str(name).lower().strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w]", "", name)
    return name


def infer_schema(df: pd.DataFrame) -> dict:
    """
    Infer schema from DataFrame.
    
    Returns schema dict with column info.
    """
    columns = []
    
    for col in df.columns:
        col_type = infer_column_type(df[col])
        nullable = bool(df[col].isna().any())  # Convert numpy bool to Python bool
        sample_values = df[col].dropna().head(5).astype(str).tolist()
        
        columns.append({
            "name": col,
            "type": col_type,
            "nullable": nullable,
            "sample_values": sample_values,
        })
    
    return {
        "columns": columns,
        "total_rows": int(len(df)),  # Convert to Python int
        "has_headers": True,
    }


def infer_column_type(series: pd.Series) -> str:
    """Infer column type from pandas Series."""
    # Drop nulls for type inference
    non_null = series.dropna()
    
    if len(non_null) == 0:
        return "string"
    
    # Check if numeric
    if pd.api.types.is_numeric_dtype(series):
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        return "number"
    
    # Check if datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    
    # Check if boolean
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    
    # Try to parse as date
    sample = non_null.head(10).astype(str)
    date_count = sum(1 for v in sample if is_date_string(v))
    if date_count > len(sample) * 0.8:
        return "date"
    
    # Default to string
    return "string"


def is_date_string(value: str) -> bool:
    """Check if string looks like a date."""
    from dateutil.parser import parse, ParserError
    
    try:
        parse(value)
        return True
    except (ParserError, ValueError):
        return False


def clean_row(row: dict) -> dict:
    """Clean row values for JSON serialization."""
    cleaned = {}
    
    for key, value in row.items():
        if pd.isna(value):
            cleaned[key] = None
        elif isinstance(value, (datetime, pd.Timestamp)):
            cleaned[key] = value.isoformat()
        elif isinstance(value, (int, float)):
            if pd.isna(value):
                cleaned[key] = None
            else:
                cleaned[key] = value
        else:
            cleaned[key] = str(value)
    
    return cleaned


def validate_row(
    row: dict,
    schema: dict,
    rules: Optional[dict] = None,
) -> list[dict]:
    """
    Validate row against schema and custom rules.
    
    Args:
        row: Row data dict
        schema: Schema dict
        rules: Optional validation rules {field: {required: bool, regex: str, etc.}}
    
    Returns:
        List of validation errors [{field: str, error: str}]
    """
    errors = []
    rules = rules or {}
    
    for col in schema["columns"]:
        name = col["name"]
        value = row.get(name)
        col_rules = rules.get(name, {})
        
        # Check required
        if col_rules.get("required") and (value is None or value == ""):
            errors.append({
                "field": name,
                "error": "Field is required",
            })
            continue
        
        # Check regex pattern
        if value and col_rules.get("regex"):
            import re
            if not re.match(col_rules["regex"], str(value)):
                errors.append({
                    "field": name,
                    "error": f"Value does not match pattern: {col_rules['regex']}",
                })
        
        # Check min/max for numbers
        if col["type"] in ("integer", "number") and value is not None:
            try:
                num_value = float(value)
                if "min" in col_rules and num_value < col_rules["min"]:
                    errors.append({
                        "field": name,
                        "error": f"Value must be >= {col_rules['min']}",
                    })
                if "max" in col_rules and num_value > col_rules["max"]:
                    errors.append({
                        "field": name,
                        "error": f"Value must be <= {col_rules['max']}",
                    })
            except (ValueError, TypeError):
                errors.append({
                    "field": name,
                    "error": "Invalid number format",
                })
    
    return errors


def normalize_value(value: Any, target_type: str) -> Any:
    """Normalize value to target type with formatting."""
    if value is None:
        return None
    
    if target_type == "date":
        from dateutil.parser import parse
        try:
            dt = parse(str(value))
            return dt.strftime("%Y-%m-%d")
        except:
            return str(value)
    
    if target_type == "currency":
        try:
            num = float(str(value).replace("$", "").replace(",", ""))
            return f"${num:,.2f}"
        except:
            return str(value)
    
    if target_type == "name":
        return str(value).title()
    
    if target_type == "uppercase":
        return str(value).upper()
    
    if target_type == "lowercase":
        return str(value).lower()
    
    return value
