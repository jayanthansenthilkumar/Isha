"""
Ishaa GraphQL Support — Basic GraphQL query execution engine.
"""

import json
import re
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ishaa.graphql")


class GraphQLSchema:
    """
    A simple GraphQL schema for the Ishaa framework.
    
    Example:
        schema = GraphQLSchema()
        
        @schema.query("hello")
        def resolve_hello(root, info, name="World"):
            return f"Hello, {name}!"
        
        @schema.query("users")
        def resolve_users(root, info):
            return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        
        @schema.mutation("createUser")
        def resolve_create_user(root, info, name, email):
            return {"id": 3, "name": name, "email": email}
        
        # Mount on app
        mount_graphql(app, schema, path="/graphql")
    """

    def __init__(self):
        self._queries: Dict[str, Callable] = {}
        self._mutations: Dict[str, Callable] = {}
        self._subscriptions: Dict[str, Callable] = {}

    def query(self, name: str):
        """Register a query resolver."""
        def decorator(func):
            self._queries[name] = func
            return func
        return decorator

    def mutation(self, name: str):
        """Register a mutation resolver."""
        def decorator(func):
            self._mutations[name] = func
            return func
        return decorator

    def subscription(self, name: str):
        """Register a subscription resolver."""
        def decorator(func):
            self._subscriptions[name] = func
            return func
        return decorator

    def execute(self, query_string: str, variables: Dict = None, context: Any = None) -> Dict:
        """
        Execute a GraphQL query.
        
        This is a simplified parser that supports:
            - query { field(args) { subfields } }
            - mutation { field(args) { subfields } }
        """
        variables = variables or {}
        result = {"data": None, "errors": []}

        try:
            # Determine operation type
            query_string = query_string.strip()

            if query_string.startswith("mutation"):
                body = self._extract_body(query_string, "mutation")
                resolvers = self._mutations
            elif query_string.startswith("query") or query_string.startswith("{"):
                body = self._extract_body(query_string, "query")
                resolvers = self._queries
            else:
                body = self._extract_body(query_string, "query")
                resolvers = self._queries

            # Parse fields
            fields = self._parse_fields(body, variables)
            data = {}

            for field_name, field_args in fields:
                resolver = resolvers.get(field_name)
                if resolver:
                    try:
                        info = {"context": context, "field_name": field_name}
                        resolved = resolver(None, info, **field_args)
                        data[field_name] = resolved
                    except Exception as e:
                        result["errors"].append({
                            "message": str(e),
                            "path": [field_name],
                        })
                        data[field_name] = None
                else:
                    result["errors"].append({
                        "message": f"Cannot query field '{field_name}'",
                        "path": [field_name],
                    })

            result["data"] = data

        except Exception as e:
            result["errors"].append({"message": str(e)})

        if not result["errors"]:
            del result["errors"]

        return result

    def _extract_body(self, query_string: str, operation: str) -> str:
        """Extract the body of a query/mutation."""
        # Remove operation type and optional name
        query_string = query_string.strip()

        brace_start = query_string.find("{")
        if brace_start == -1:
            return ""

        # Find matching closing brace
        depth = 0
        body_start = brace_start + 1
        for i in range(brace_start, len(query_string)):
            if query_string[i] == "{":
                depth += 1
            elif query_string[i] == "}":
                depth -= 1
                if depth == 0:
                    return query_string[body_start:i].strip()

        return query_string[body_start:].strip()

    def _parse_fields(self, body: str, variables: Dict) -> List[tuple]:
        """Parse field selections from the query body."""
        fields = []
        pos = 0

        while pos < len(body):
            # Skip whitespace
            while pos < len(body) and body[pos] in " \t\n\r,":
                pos += 1

            if pos >= len(body):
                break

            # Read field name
            name_start = pos
            while pos < len(body) and body[pos] not in " \t\n\r({},":
                pos += 1

            field_name = body[name_start:pos].strip()
            if not field_name:
                pos += 1
                continue

            # Parse arguments
            args = {}
            while pos < len(body) and body[pos] in " \t\n\r":
                pos += 1

            if pos < len(body) and body[pos] == "(":
                args_end = body.find(")", pos)
                if args_end != -1:
                    args_str = body[pos + 1:args_end]
                    args = self._parse_args(args_str, variables)
                    pos = args_end + 1

            # Skip sub-selection (we resolve the full object)
            if pos < len(body) and body[pos] == "{":
                depth = 1
                pos += 1
                while pos < len(body) and depth > 0:
                    if body[pos] == "{":
                        depth += 1
                    elif body[pos] == "}":
                        depth -= 1
                    pos += 1

            if field_name:
                fields.append((field_name, args))

        return fields

    def _parse_args(self, args_str: str, variables: Dict) -> Dict:
        """Parse argument string like 'name: "Alice", age: 30'."""
        args = {}
        for part in self._split_args(args_str):
            part = part.strip()
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Variable reference
            if value.startswith("$"):
                var_name = value[1:]
                args[key] = variables.get(var_name)
            # String
            elif (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                args[key] = value[1:-1]
            # Boolean
            elif value.lower() == "true":
                args[key] = True
            elif value.lower() == "false":
                args[key] = False
            elif value.lower() == "null":
                args[key] = None
            # Number
            else:
                try:
                    args[key] = int(value)
                except ValueError:
                    try:
                        args[key] = float(value)
                    except ValueError:
                        args[key] = value

        return args

    def _split_args(self, args_str: str) -> List[str]:
        """Split arguments respecting nested structures."""
        parts = []
        current = ""
        depth = 0
        in_string = False
        string_char = None

        for ch in args_str:
            if in_string:
                current += ch
                if ch == string_char:
                    in_string = False
            elif ch in ('"', "'"):
                in_string = True
                string_char = ch
                current += ch
            elif ch in ("[", "{"):
                depth += 1
                current += ch
            elif ch in ("]", "}"):
                depth -= 1
                current += ch
            elif ch == "," and depth == 0:
                parts.append(current)
                current = ""
            else:
                current += ch

        if current.strip():
            parts.append(current)

        return parts


def mount_graphql(app, schema: GraphQLSchema, path: str = "/graphql"):
    """
    Mount a GraphQL endpoint on the Ishaa app.
    
    Supports:
        - POST requests with JSON body: {"query": "...", "variables": {...}}
        - GET requests with query string: ?query=...&variables=...
    """
    from .response import JSONResponse, HTMLResponse

    @app.route(path, methods=["GET", "POST"])
    async def graphql_endpoint(request):
        if request.method == "GET":
            # Check for query in query params
            query = request.query_params.get("query")
            if not query:
                # Serve GraphiQL IDE
                return HTMLResponse(_graphiql_html(path))

            variables = request.query_params.get("variables", "{}")
            try:
                variables = json.loads(variables)
            except (json.JSONDecodeError, TypeError):
                variables = {}
        else:
            # POST request
            body = await request.json()
            query = body.get("query", "")
            variables = body.get("variables", {})

        result = schema.execute(query, variables, context=request)
        status = 200 if "errors" not in result else 400
        return JSONResponse(result, status_code=status)


def _graphiql_html(endpoint: str) -> str:
    """Generate GraphiQL IDE HTML page."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Ishaa GraphQL IDE</title>
    <link href="https://unpkg.com/graphiql/graphiql.min.css" rel="stylesheet" />
</head>
<body style="margin: 0; height: 100vh;">
    <div id="graphiql" style="height: 100vh;"></div>
    <script crossorigin src="https://unpkg.com/react/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
    <script>
        const fetcher = GraphiQL.createFetcher({{ url: '{endpoint}' }});
        ReactDOM.render(
            React.createElement(GraphiQL, {{ fetcher }}),
            document.getElementById('graphiql'),
        );
    </script>
</body>
</html>"""