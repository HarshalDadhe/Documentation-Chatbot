# Extracting metadata, SQL strings, function, classes from Python script.
import ast
import re
import json

def extract_sql_queries(source: str) -> list:
    """Extract SQL strings using regex (handles multi-line SQL)."""
    # Find triple quoted strings, then find sql pattern in those.
    sql_pattern = re.compile(
        r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)\b[\s\S]+?(?="""|\'\'\' |$)',
        re.IGNORECASE
    )

    # Find all triple-quoted strings
    strings = re.findall(r'"""([\s\S]*?)"""|\'\'\'([\s\S]*?)\'\'\'', source)

    sql_queries = []
    for s in strings:
        content = s[0] or s[1] # triple quotes query or triple single quotes, whatever is present.
        # Now actually USE sql_pattern instead of a redundant re.search
        match = sql_pattern.search(content)
        if match:
            sql_queries.append(content.strip())

    return sql_queries


def extract_airflow_metadata(source: str) -> dict:
    """Extract DAG id, schedule, tasks, operators."""
    metadata = {
        "dag": [],
        "schedule_interval": [],
        "operators_used": [],
        "task_id": []
    }
    """
    # DAG id
    #dag_match = re.search(r'dag\s*=\s*["\'](.+?)["\']', source)
    dag_match = re.search(r'\bdag\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\b', source)
    if dag_match:
        metadata["dag"] = dag_match.group(1)
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "dag":
                    if isinstance(kw.value, ast.Name):
                        metadata["dag"] = kw.value.id

    # Schedule
    #schedule_match = re.search(r'schedule_interval\s*=\s*["\'](.+?)["\']', source)
    schedule_match = re.search(r'\bschedule_interval\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\b', source)
    if schedule_match:
        metadata["schedule_interval"] = schedule_match.group(1)

    # Operators
    operators = re.findall(r'from airflow\.operators\.\S+ import (\w+)', source)
    operators += re.findall(r'from airflow\.providers\.\S+ import (\w+)', source)
    metadata["operators_used"] = list(set(operators))

    # task id
    task_id_match = re.findall(r'task_id\s*=\s*["\'](.+?)["\']', source)
    metadata["task_id"] = list(set(task_id_match))

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
result = script_to_json("source/CUSTOMER.py")
print(json.dumps(result, indent=2))

