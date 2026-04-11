# Extracting metadata, SQL strings, function, classes from Python script.
import ast
import re
import json

def extract_sql_queries(source: str) -> list:
    """Extract SQL strings using regex (handles multi-line SQL)."""
    sql_pattern = re.compile(
        r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)[\s\S]+?(?="""\'\'\'|$)',
        re.IGNORECASE
    )
    # Find all triple-quoted strings containing SQL
    strings = re.findall(r'"""([\s\S]*?)"""|\'\'\'([\s\S]*?)\'\'\'', source)
    sql_queries = []
    for s in strings:
        content = s[0] or s[1]
        if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|WITH)\b', content, re.IGNORECASE):
            sql_queries.append(content.strip())
    return sql_queries


def extract_airflow_metadata(source: str) -> dict:
    """Extract DAG id, schedule, tasks, operators."""
    metadata = {
        "dag_id": None,
        "schedule_interval": None,
        "operators_used": [],
        "tasks": []
    }

    # DAG id
    dag_id_match = re.search(r'dag_id\s*=\s*["\'](.+?)["\']', source)
    if dag_id_match:
        metadata["dag_id"] = dag_id_match.group(1)

    # Schedule
    schedule_match = re.search(r'schedule_interval\s*=\s*["\'](.+?)["\']', source)
    if schedule_match:
        metadata["schedule_interval"] = schedule_match.group(1)

    # Operators
    operators = re.findall(r'from airflow\.operators\.\S+ import (\w+)', source)
    operators += re.findall(r'from airflow\.providers\.\S+ import (\w+)', source)
    metadata["operators_used"] = list(set(operators))

    return metadata


def parse_functions(source: str) -> list:
    """Extract all function names, args, docstrings."""
    tree = ast.parse(source)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node) or "",
                "line_number": node.lineno
            })
    return functions

# Converting the data to JSON format.
def script_to_json(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    structured = {
        "file_name": file_path.split("/")[-1],
        "module_docstring": ast.get_docstring(tree) or "",
        "imports": [],
        "airflow_metadata": extract_airflow_metadata(source),
        "functions": parse_functions(source),
        "sql_queries": extract_sql_queries(source),
        "classes": []
    }

    # Imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            structured["imports"] += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            structured["imports"].append(f"from {node.module} import ...")

    # Classes
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            structured["classes"].append({
                "name": node.name,
                "docstring": ast.get_docstring(node) or "",
                "methods": [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
            })

    return structured

# Run it
result = script_to_json("my_dag.py")
print(json.dumps(result, indent=2))

