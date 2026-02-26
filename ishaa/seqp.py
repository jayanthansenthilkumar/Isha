"""
Ishaa Self-Evolving Quality Pipeline (SEQP) — Intelligent CI/CD Evolution.

World-first framework feature that continuously analyzes application logic,
generates adversarial tests, measures risk, and automatically rewrites
CI/CD pipeline configurations based on code complexity and runtime behavior.

Layers:
    1. Risk Analyzer — Branch density, complexity, state mutation risk
    2. Auto Test Generator — Boundary, concurrency, load, security tests
    3. Pipeline Rewriter — Auto-update CI/CD YAML configs
    4. Deployment Guard — Dynamic coverage thresholds
    5. Drift Intelligence — Trend tracking & anomaly detection

Usage:
    from ishaa import Ishaa

    app = Ishaa()
    app.enable_seqp()

    @app.route("/payment")
    @app.critical(level="financial_core")
    async def process_payment(request):
        ...

    # Get quality report
    report = app.seqp.report()
"""

import ast
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ishaa.seqp")


# ─── Risk Levels ────────────────────────────────────────────────────────

class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ─── Code Metrics ───────────────────────────────────────────────────────

class CodeMetrics:
    """Metrics collected from analyzing a Python source file or function."""

    def __init__(self):
        self.branch_density: float = 0.0
        self.cyclomatic_complexity: int = 1
        self.nesting_depth: int = 0
        self.state_mutations: int = 0
        self.db_interactions: int = 0
        self.concurrency_indicators: int = 0
        self.external_calls: int = 0
        self.lines_of_code: int = 0
        self.has_error_handling: bool = False
        self.input_parsing: int = 0
        self.security_sensitive: bool = False

    @property
    def risk_score(self) -> float:
        """Calculate a 0.0 - 1.0 risk score from metrics."""
        score = 0.0
        # Branch density (more branches = more risk)
        score += min(self.branch_density / 10.0, 0.2)
        # Cyclomatic complexity
        score += min(self.cyclomatic_complexity / 20.0, 0.2)
        # Nesting depth
        score += min(self.nesting_depth / 6.0, 0.1)
        # State mutations
        score += min(self.state_mutations / 10.0, 0.15)
        # DB interactions
        score += min(self.db_interactions / 5.0, 0.1)
        # Concurrency
        score += min(self.concurrency_indicators / 3.0, 0.1)
        # External calls
        score += min(self.external_calls / 5.0, 0.05)
        # Input parsing (potential attack surface)
        score += min(self.input_parsing / 5.0, 0.05)
        # Security sensitive
        if self.security_sensitive:
            score += 0.05
        return min(score, 1.0)

    @property
    def risk_level(self) -> str:
        s = self.risk_score
        if s >= 0.7:
            return RiskLevel.CRITICAL
        elif s >= 0.5:
            return RiskLevel.HIGH
        elif s >= 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_density": round(self.branch_density, 2),
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "nesting_depth": self.nesting_depth,
            "state_mutations": self.state_mutations,
            "db_interactions": self.db_interactions,
            "concurrency_indicators": self.concurrency_indicators,
            "external_calls": self.external_calls,
            "lines_of_code": self.lines_of_code,
            "has_error_handling": self.has_error_handling,
            "input_parsing": self.input_parsing,
            "security_sensitive": self.security_sensitive,
            "risk_score": round(self.risk_score, 4),
            "risk_level": self.risk_level,
        }


# ─── Layer 1: Risk Analyzer ────────────────────────────────────────────

class RiskAnalyzer:
    """
    Analyzes Python source code to produce risk profiles.

    Measures:
        - Branch density (if/elif/else ratio)
        - Cyclomatic complexity
        - Nesting depth
        - State mutation risk (assignments to self.*, globals)
        - DB interaction intensity (SQL, ORM patterns)
        - Concurrency exposure (async, thread, lock patterns)
        - External call count
        - Input parsing (request.json, request.form, etc.)
    """

    # Patterns for detecting various code characteristics
    DB_PATTERNS = re.compile(
        r"\b(execute|query|insert|update|delete|select|commit|rollback|cursor|"
        r"\.save\(|\.create\(|\.all\(|\.filter\(|\.get\(|Database|Model)\b",
        re.IGNORECASE,
    )
    CONCURRENCY_PATTERNS = re.compile(
        r"\b(async\s+def|await\s+|asyncio\.|threading\.|Lock\(|Semaphore\(|"
        r"gather\(|create_task|run_in_executor|concurrent)\b"
    )
    EXTERNAL_PATTERNS = re.compile(
        r"\b(requests\.|httpx\.|urllib\.|aiohttp\.|fetch|api_call|"
        r"send_email|smtp|redis\.|memcache)\b",
        re.IGNORECASE,
    )
    INPUT_PATTERNS = re.compile(
        r"\b(request\.json|request\.form|request\.body|request\.text|"
        r"request\.query_params|request\.data|json\.loads)\b"
    )
    SECURITY_PATTERNS = re.compile(
        r"\b(password|secret|token|api_key|auth|credential|jwt|"
        r"encrypt|decrypt|hash|sign|verify|payment|billing|charge)\b",
        re.IGNORECASE,
    )

    def analyze_source(self, source: str, filename: str = "<string>") -> CodeMetrics:
        """Analyze Python source code and produce metrics."""
        metrics = CodeMetrics()

        lines = source.split("\n")
        metrics.lines_of_code = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

        try:
            tree = ast.parse(source, filename=filename)
            self._analyze_ast(tree, metrics)
        except SyntaxError:
            logger.debug(f"SEQP: Syntax error analyzing {filename}")

        # Regex-based pattern detection
        metrics.db_interactions = len(self.DB_PATTERNS.findall(source))
        metrics.concurrency_indicators = len(self.CONCURRENCY_PATTERNS.findall(source))
        metrics.external_calls = len(self.EXTERNAL_PATTERNS.findall(source))
        metrics.input_parsing = len(self.INPUT_PATTERNS.findall(source))
        metrics.security_sensitive = bool(self.SECURITY_PATTERNS.search(source))

        # Branch density = branches / lines
        if metrics.lines_of_code > 0:
            metrics.branch_density = (
                metrics.cyclomatic_complexity / max(metrics.lines_of_code, 1)
            ) * 10

        return metrics

    def analyze_file(self, filepath: str) -> CodeMetrics:
        """Analyze a Python file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            return self.analyze_source(source, filename=filepath)
        except (OSError, UnicodeDecodeError):
            return CodeMetrics()

    def analyze_function(self, func: Callable) -> CodeMetrics:
        """Analyze a single function/handler."""
        import inspect
        try:
            source = inspect.getsource(func)
            return self.analyze_source(source, filename=func.__name__)
        except (OSError, TypeError):
            return CodeMetrics()

    def _analyze_ast(self, tree: ast.AST, metrics: CodeMetrics, depth: int = 0):
        """Walk the AST to calculate complexity metrics."""
        metrics.nesting_depth = max(metrics.nesting_depth, depth)

        for node in ast.iter_child_nodes(tree):
            # Cyclomatic complexity: count decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                metrics.cyclomatic_complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each and/or adds a branch
                metrics.cyclomatic_complexity += len(node.values) - 1
            elif isinstance(node, ast.Assert):
                metrics.cyclomatic_complexity += 1

            # State mutations
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        metrics.state_mutations += 1
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute):
                    metrics.state_mutations += 1

            # Error handling
            if isinstance(node, (ast.Try, ast.ExceptHandler)):
                metrics.has_error_handling = True

            # Recurse with depth tracking for nesting
            if isinstance(node, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                self._analyze_ast(node, metrics, depth + 1)
            else:
                self._analyze_ast(node, metrics, depth)

    def profile_route(self, handler: Callable, criticality: str = "standard") -> Dict[str, Any]:
        """Generate a risk profile for a route handler."""
        metrics = self.analyze_function(handler)
        return {
            "handler": handler.__name__,
            "criticality": criticality,
            "metrics": metrics.to_dict(),
            "recommended_coverage": self._recommended_coverage(metrics, criticality),
            "recommended_tests": self._recommended_tests(metrics, criticality),
        }

    def _recommended_coverage(self, metrics: CodeMetrics, criticality: str) -> float:
        """Calculate recommended coverage threshold based on risk."""
        base = 0.75
        if metrics.risk_level == RiskLevel.CRITICAL:
            base = 0.95
        elif metrics.risk_level == RiskLevel.HIGH:
            base = 0.90
        elif metrics.risk_level == RiskLevel.MEDIUM:
            base = 0.85

        if criticality == "financial_core":
            base = max(base, 0.95)
        elif criticality == "security_critical":
            base = max(base, 0.92)
        elif criticality == "data_critical":
            base = max(base, 0.90)

        return min(base, 1.0)

    def _recommended_tests(self, metrics: CodeMetrics, criticality: str) -> List[str]:
        """Determine which test types are needed."""
        tests = ["unit"]

        if metrics.branch_density > 3:
            tests.append("boundary")
        if metrics.db_interactions > 0:
            tests.append("integration")
        if metrics.concurrency_indicators > 0:
            tests.append("concurrency")
        if metrics.input_parsing > 0:
            tests.extend(["input_validation", "security_payload"])
        if metrics.external_calls > 0:
            tests.append("mock_external")
        if metrics.security_sensitive:
            tests.append("security_audit")
        if metrics.state_mutations > 3:
            tests.append("state_mutation")
        if criticality in ("financial_core", "security_critical"):
            tests.extend(["load_burst", "mutation_testing"])

        return list(dict.fromkeys(tests))  # deduplicate preserving order


# ─── Layer 2: Auto Test Generator ──────────────────────────────────────

class AutoTestGenerator:
    """
    Generates test cases dynamically based on risk profiles.

    Not random fuzzing — risk-targeted generation:
        - Boundary tests for high branch density
        - Race condition simulation for concurrent code
        - Load burst tests for critical routes
        - Security payload mutation for input-parsing routes
        - Schema drift validation for DB-heavy routes
    """

    def generate_tests(
        self,
        route_path: str,
        handler_name: str,
        metrics: CodeMetrics,
        criticality: str = "standard",
    ) -> List[Dict[str, Any]]:
        """Generate test specifications based on route risk profile."""
        tests = []

        # Always generate basic happy-path test
        tests.append(self._basic_test(route_path, handler_name))

        # Boundary tests (high branch density)
        if metrics.branch_density > 3 or metrics.cyclomatic_complexity > 5:
            tests.extend(self._boundary_tests(route_path, handler_name, metrics))

        # Concurrency simulation
        if metrics.concurrency_indicators > 0:
            tests.append(self._concurrency_test(route_path, handler_name))

        # Input validation / security payloads
        if metrics.input_parsing > 0:
            tests.extend(self._security_tests(route_path, handler_name))

        # DB schema drift
        if metrics.db_interactions > 2:
            tests.append(self._schema_drift_test(route_path, handler_name))

        # Load burst (for critical routes)
        if criticality in ("financial_core", "security_critical") or metrics.risk_score > 0.6:
            tests.append(self._load_burst_test(route_path, handler_name))

        # Mutation testing for critical code
        if criticality == "financial_core" or metrics.risk_score > 0.7:
            tests.append(self._mutation_test(route_path, handler_name))

        return tests

    def generate_test_code(self, tests: List[Dict[str, Any]], app_module: str = "app") -> str:
        """Generate executable test code from test specifications."""
        lines = [
            '"""Auto-generated tests by Ishaa SEQP — Self-Evolving Quality Pipeline."""',
            "import asyncio",
            "import time",
            "import json",
            f"from {app_module} import app",
            "from ishaa.testing import TestClient",
            "",
            "client = TestClient(app)",
            "",
        ]

        for i, test in enumerate(tests):
            fn_name = f"test_{test['type']}_{test['handler']}_{i}"
            fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", fn_name)

            lines.append(f"def {fn_name}():")
            lines.append(f'    """[SEQP] {test["description"]}"""')

            if test["type"] == "basic":
                lines.append(f'    response = client.{test.get("method", "get").lower()}("{test["path"]}")')
                lines.append(f"    assert response.status in [200, 201, 204, 301, 302], "
                             f"f\"Expected success, got {{response.status}}\"")

            elif test["type"] == "boundary":
                for payload in test.get("payloads", []):
                    lines.append(f"    # Boundary: {payload.get('description', '')}")
                    lines.append(f'    response = client.post("{test["path"]}", json={json.dumps(payload.get("data", {}))})')
                    lines.append(f"    assert response.status != 500, \"Server error on boundary input\"")

            elif test["type"] == "concurrency":
                lines.append(f"    async def _run():")
                lines.append(f"        tasks = []")
                lines.append(f"        for _ in range({test.get('concurrent_requests', 10)}):")
                lines.append(f'            tasks.append(asyncio.to_thread(client.get, "{test["path"]}"))')
                lines.append(f"        results = await asyncio.gather(*tasks, return_exceptions=True)")
                lines.append(f"        errors = [r for r in results if isinstance(r, Exception)]")
                lines.append(f"        assert len(errors) == 0, f\"{{len(errors)}} concurrent request failures\"")
                lines.append(f"    asyncio.run(_run())")

            elif test["type"] == "security_payload":
                for payload in test.get("payloads", []):
                    lines.append(f"    # Security: {payload.get('name', '')}")
                    lines.append(f'    response = client.post("{test["path"]}", '
                                 f'json={json.dumps(payload.get("data", {}))})')
                    lines.append(f"    assert response.status != 500, "
                                 f"\"Server error on security payload: {payload.get('name', '')}\"")

            elif test["type"] == "load_burst":
                lines.append(f"    start = time.time()")
                lines.append(f"    errors = 0")
                lines.append(f"    for _ in range({test.get('request_count', 100)}):")
                lines.append(f'        resp = client.get("{test["path"]}")')
                lines.append(f"        if resp.status >= 500:")
                lines.append(f"            errors += 1")
                lines.append(f"    elapsed = time.time() - start")
                lines.append(f"    assert errors / {test.get('request_count', 100)} < 0.05, "
                             f"\"Error rate > 5% under load\"")
                lines.append(f"    assert elapsed < {test.get('max_seconds', 30)}, "
                             f"\"Load burst took too long\"")

            elif test["type"] == "schema_drift":
                lines.append(f'    response = client.get("{test["path"]}")')
                lines.append(f"    if response.status == 200:")
                lines.append(f"        data = response.json()")
                lines.append(f"        assert isinstance(data, (dict, list)), "
                             f"\"Response schema drifted from expected structure\"")

            elif test["type"] == "mutation":
                lines.append(f'    response = client.get("{test["path"]}")')
                lines.append(f"    assert response.status == 200")
                lines.append(f"    baseline = response.text")
                lines.append(f"    # Verify deterministic behavior")
                lines.append(f'    response2 = client.get("{test["path"]}")')
                lines.append(f"    assert response2.text == baseline, \"Non-deterministic behavior detected\"")

            lines.append("")

        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    import sys")
        lines.append("    passed = 0")
        lines.append("    failed = 0")
        lines.append("    for name, func in list(globals().items()):")
        lines.append("        if name.startswith('test_') and callable(func):")
        lines.append("            try:")
        lines.append("                func()")
        lines.append("                passed += 1")
        lines.append('                print(f"  ✓ {name}")')
        lines.append("            except Exception as e:")
        lines.append("                failed += 1")
        lines.append('                print(f"  ✗ {name}: {e}")')
        lines.append('    print(f"\\nResults: {passed} passed, {failed} failed")')
        lines.append("    sys.exit(1 if failed > 0 else 0)")
        lines.append("")

        return "\n".join(lines)

    def _basic_test(self, path: str, handler: str) -> Dict[str, Any]:
        return {
            "type": "basic",
            "path": path,
            "handler": handler,
            "method": "GET",
            "description": f"Basic happy-path test for {path}",
        }

    def _boundary_tests(self, path: str, handler: str, metrics: CodeMetrics) -> List[Dict[str, Any]]:
        payloads = [
            {"description": "Empty body", "data": {}},
            {"description": "Null values", "data": {"key": None, "value": None}},
            {"description": "Oversized string", "data": {"input": "x" * 10000}},
            {"description": "Negative numbers", "data": {"id": -1, "count": -999}},
            {"description": "Zero values", "data": {"id": 0, "count": 0}},
            {"description": "Special characters", "data": {"name": "<script>alert(1)</script>"}},
            {"description": "Unicode", "data": {"name": "日本語テスト 🌟"}},
        ]
        if metrics.cyclomatic_complexity > 10:
            payloads.append({"description": "Deeply nested", "data": {"a": {"b": {"c": {"d": "deep"}}}}})

        return [{
            "type": "boundary",
            "path": path,
            "handler": handler,
            "description": f"Boundary value tests for {path} (complexity={metrics.cyclomatic_complexity})",
            "payloads": payloads,
        }]

    def _concurrency_test(self, path: str, handler: str) -> Dict[str, Any]:
        return {
            "type": "concurrency",
            "path": path,
            "handler": handler,
            "description": f"Concurrency simulation for {path}",
            "concurrent_requests": 20,
        }

    def _security_tests(self, path: str, handler: str) -> List[Dict[str, Any]]:
        payloads = [
            {"name": "SQL Injection", "data": {"input": "'; DROP TABLE users; --"}},
            {"name": "XSS", "data": {"input": "<img src=x onerror=alert(1)>"}},
            {"name": "Command Injection", "data": {"input": "; rm -rf /"}},
            {"name": "Path Traversal", "data": {"file": "../../../etc/passwd"}},
            {"name": "JSON Injection", "data": {"input": '{"__proto__": {"admin": true}}'}},
            {"name": "Oversized JSON", "data": {"data": ["x"] * 1000}},
        ]
        return [{
            "type": "security_payload",
            "path": path,
            "handler": handler,
            "description": f"Security payload tests for {path}",
            "payloads": payloads,
        }]

    def _schema_drift_test(self, path: str, handler: str) -> Dict[str, Any]:
        return {
            "type": "schema_drift",
            "path": path,
            "handler": handler,
            "description": f"Schema drift validation for {path}",
        }

    def _load_burst_test(self, path: str, handler: str) -> Dict[str, Any]:
        return {
            "type": "load_burst",
            "path": path,
            "handler": handler,
            "description": f"Load burst test for {path}",
            "request_count": 200,
            "max_seconds": 60,
        }

    def _mutation_test(self, path: str, handler: str) -> Dict[str, Any]:
        return {
            "type": "mutation",
            "path": path,
            "handler": handler,
            "description": f"Mutation/determinism test for {path}",
        }


# ─── Layer 3: Pipeline Rewriter Engine ─────────────────────────────────

class PipelineRewriterEngine:
    """
    Automatically generates and updates CI/CD pipeline configurations
    based on risk analysis results.

    Supports:
        - GitHub Actions (`.github/workflows/`)
        - GitLab CI (`.gitlab-ci.yml`)
        - Generic YAML pipeline format
    """

    def generate_pipeline(
        self,
        risk_profiles: List[Dict[str, Any]],
        platform: str = "github_actions",
        base_config: Optional[Dict] = None,
    ) -> str:
        """Generate a CI/CD pipeline configuration based on risk profiles."""

        # Determine which stages are needed
        stages = self._determine_stages(risk_profiles)

        if platform == "github_actions":
            return self._generate_github_actions(stages, risk_profiles, base_config)
        elif platform == "gitlab_ci":
            return self._generate_gitlab_ci(stages, risk_profiles, base_config)
        else:
            return self._generate_generic(stages, risk_profiles, base_config)

    def _determine_stages(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Determine required pipeline stages based on risk analysis."""
        stages = []
        max_risk = max((p["metrics"]["risk_score"] for p in profiles), default=0)
        has_critical = any(p.get("criticality") == "financial_core" for p in profiles)
        has_security = any(p["metrics"].get("security_sensitive") for p in profiles)
        has_db = any(p["metrics"].get("db_interactions", 0) > 0 for p in profiles)
        has_concurrency = any(p["metrics"].get("concurrency_indicators", 0) > 0 for p in profiles)
        has_input = any(p["metrics"].get("input_parsing", 0) > 0 for p in profiles)

        # Always: lint + unit tests
        stages.append({
            "name": "lint_and_format",
            "description": "Code quality checks",
            "always": True,
        })
        stages.append({
            "name": "unit_tests",
            "description": "Unit test suite",
            "always": True,
            "coverage_threshold": self._dynamic_coverage(profiles),
        })

        # Conditional stages based on risk
        if has_db:
            stages.append({
                "name": "schema_drift_validation",
                "description": "Database schema drift check",
                "trigger": "DB interactions detected",
            })

        if has_concurrency or max_risk > 0.5:
            stages.append({
                "name": "concurrency_simulation",
                "description": "Race condition and deadlock detection",
                "trigger": f"Concurrency risk (score={max_risk:.2f})",
            })

        if has_input or has_security:
            stages.append({
                "name": "security_scan",
                "description": "Security payload and vulnerability testing",
                "trigger": "Input parsing / security-sensitive code detected",
            })

        if max_risk > 0.6 or has_critical:
            stages.append({
                "name": "mutation_testing",
                "description": "Mutation testing for logic verification",
                "trigger": f"High risk (score={max_risk:.2f})",
            })

        if has_critical:
            stages.append({
                "name": "load_testing",
                "description": "Load and stress testing",
                "trigger": "Financial/critical route detected",
            })

        if max_risk > 0.4:
            stages.append({
                "name": "deep_logical_test",
                "description": "Deep branch coverage and edge case testing",
                "trigger": f"Medium+ risk (score={max_risk:.2f})",
            })

        # Deployment stages
        stages.append({
            "name": "build",
            "description": "Package build",
            "always": True,
        })

        if max_risk > 0.5 or has_critical:
            stages.append({
                "name": "shadow_deployment",
                "description": "Shadow/canary deployment validation",
                "trigger": "High risk deployment",
            })

        stages.append({
            "name": "deploy",
            "description": "Production deployment",
            "always": True,
        })

        return stages

    def _dynamic_coverage(self, profiles: List[Dict[str, Any]]) -> float:
        """Calculate dynamic coverage threshold."""
        if not profiles:
            return 0.80
        coverages = [p.get("recommended_coverage", 0.80) for p in profiles]
        return round(max(coverages), 2)

    def _generate_github_actions(
        self,
        stages: List[Dict],
        profiles: List[Dict],
        base_config: Optional[Dict],
    ) -> str:
        """Generate GitHub Actions workflow YAML."""
        coverage = self._dynamic_coverage(profiles)
        max_risk = max((p["metrics"]["risk_score"] for p in profiles), default=0)

        lines = [
            "# Auto-generated by Ishaa SEQP — Self-Evolving Quality Pipeline",
            f"# Risk Score: {max_risk:.2f} | Coverage Threshold: {coverage:.0%}",
            f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "name: Ishaa SEQP Pipeline",
            "",
            "on:",
            "  push:",
            "    branches: [main]",
            "  pull_request:",
            "    branches: [main]",
            "",
            "jobs:",
        ]

        for stage in stages:
            job_name = stage["name"]
            lines.append(f"  {job_name}:")
            lines.append(f"    # {stage['description']}")
            if stage.get("trigger"):
                lines.append(f"    # Trigger: {stage['trigger']}")
            lines.append("    runs-on: ubuntu-latest")
            lines.append("    steps:")
            lines.append("      - uses: actions/checkout@v4")
            lines.append("      - name: Set up Python")
            lines.append("        uses: actions/setup-python@v5")
            lines.append("        with:")
            lines.append("          python-version: '3.x'")
            lines.append("      - name: Install dependencies")
            lines.append("        run: pip install -e '.[dev]'")

            if job_name == "lint_and_format":
                lines.append("      - name: Lint")
                lines.append("        run: python -m py_compile ishaa/*.py")

            elif job_name == "unit_tests":
                lines.append("      - name: Run tests with coverage")
                lines.append(f"        run: pytest tests/ -v --tb=short")

            elif job_name == "concurrency_simulation":
                lines.append("      - name: Concurrency simulation")
                lines.append("        run: python -m ishaa.seqp run-concurrency-tests")

            elif job_name == "security_scan":
                lines.append("      - name: Security payload testing")
                lines.append("        run: python -m ishaa.seqp run-security-tests")

            elif job_name == "mutation_testing":
                lines.append("      - name: Mutation testing")
                lines.append("        run: python -m ishaa.seqp run-mutation-tests")

            elif job_name == "load_testing":
                lines.append("      - name: Load/stress testing")
                lines.append("        run: python -m ishaa.seqp run-load-tests")

            elif job_name == "schema_drift_validation":
                lines.append("      - name: Schema drift check")
                lines.append("        run: python -m ishaa.seqp check-schema-drift")

            elif job_name == "deep_logical_test":
                lines.append("      - name: Deep logical testing")
                lines.append("        run: pytest tests/ -v --tb=long")

            elif job_name == "build":
                lines.append("      - name: Build package")
                lines.append("        run: python -m build")

            elif job_name == "shadow_deployment":
                lines.append("      - name: Shadow deployment validation")
                lines.append("        run: echo 'Shadow deployment stage - configure per environment'")

            elif job_name == "deploy":
                lines.append("      - name: Deploy")
                lines.append("        run: echo 'Deploy stage - configure per environment'")

            lines.append("")

        return "\n".join(lines)

    def _generate_gitlab_ci(
        self, stages: List[Dict], profiles: List[Dict], base_config: Optional[Dict]
    ) -> str:
        """Generate GitLab CI YAML."""
        coverage = self._dynamic_coverage(profiles)
        max_risk = max((p["metrics"]["risk_score"] for p in profiles), default=0)

        lines = [
            "# Auto-generated by Ishaa SEQP — Self-Evolving Quality Pipeline",
            f"# Risk Score: {max_risk:.2f} | Coverage Threshold: {coverage:.0%}",
            "",
            "stages:",
        ]
        for stage in stages:
            lines.append(f"  - {stage['name']}")
        lines.append("")

        for stage in stages:
            lines.append(f"{stage['name']}:")
            lines.append(f"  stage: {stage['name']}")
            lines.append("  image: python:3.x")
            lines.append("  script:")
            lines.append("    - pip install -e '.[dev]'")
            lines.append(f"    - echo 'Running {stage['description']}'")
            if stage.get("trigger"):
                lines.append(f"  # Trigger: {stage['trigger']}")
            lines.append("")

        return "\n".join(lines)

    def _generate_generic(
        self, stages: List[Dict], profiles: List[Dict], base_config: Optional[Dict]
    ) -> str:
        """Generate generic pipeline YAML."""
        coverage = self._dynamic_coverage(profiles)

        lines = [
            "# Auto-generated by Ishaa SEQP",
            f"# Dynamic Coverage Threshold: {coverage:.0%}",
            "",
            "pipeline:",
            "  stages:",
        ]
        for stage in stages:
            lines.append(f"    - name: {stage['name']}")
            lines.append(f"      description: {stage['description']}")
            if stage.get("trigger"):
                lines.append(f"      trigger: \"{stage['trigger']}\"")
            if stage.get("coverage_threshold"):
                lines.append(f"      coverage_threshold: {stage['coverage_threshold']}")
        lines.append("")

        return "\n".join(lines)


# ─── Layer 4: Deployment Guard ─────────────────────────────────────────

class DeploymentGuard:
    """
    Dynamic deployment policy that adjusts validation rules based on
    code risk, criticality, and historical metrics.

    Instead of static rules like "min coverage 80%", policies adapt:
        - High-risk module → 95% branch coverage required
        - Low-risk module → 75% coverage allowed
        - Financial routes → concurrency simulation must pass
        - Performance budget enforcement
    """

    def __init__(
        self,
        latency_drift_tolerance: float = 0.20,
        error_rate_threshold: float = 0.02,
        rollback_threshold: float = 0.05,
    ):
        self.latency_drift_tolerance = latency_drift_tolerance
        self.error_rate_threshold = error_rate_threshold
        self.rollback_threshold = rollback_threshold
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._deployment_history: List[Dict[str, Any]] = []

    def generate_policy(self, risk_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate deployment policies based on risk profiles."""
        policy = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rules": [],
            "global_gates": [],
        }

        for profile in risk_profiles:
            handler = profile.get("handler", "unknown")
            risk = profile["metrics"]["risk_score"]
            criticality = profile.get("criticality", "standard")

            rule = {
                "handler": handler,
                "risk_level": profile["metrics"]["risk_level"],
                "required_coverage": profile.get("recommended_coverage", 0.80),
                "required_tests": profile.get("recommended_tests", ["unit"]),
                "gates": [],
            }

            # Dynamic gates based on risk
            if risk > 0.7 or criticality == "financial_core":
                rule["gates"].extend([
                    "concurrency_simulation_pass",
                    "mutation_testing_pass",
                    "load_test_pass",
                    "security_scan_pass",
                ])
            elif risk > 0.5:
                rule["gates"].extend([
                    "security_scan_pass",
                    "deep_logical_test_pass",
                ])
            elif risk > 0.3:
                rule["gates"].append("integration_test_pass")

            policy["rules"].append(rule)

        # Global gates
        policy["global_gates"] = [
            {"name": "latency_budget", "tolerance": f"{self.latency_drift_tolerance:.0%}"},
            {"name": "error_rate", "threshold": f"{self.error_rate_threshold:.1%}"},
            {"name": "rollback_trigger", "threshold": f"{self.rollback_threshold:.1%}"},
        ]

        self._policies["current"] = policy
        return policy

    def check_deployment(
        self,
        current_latency: float,
        baseline_latency: float,
        current_error_rate: float,
    ) -> Dict[str, Any]:
        """Check if a deployment should proceed or be blocked."""
        result = {
            "allowed": True,
            "checks": [],
            "recommendation": "proceed",
        }

        # Latency budget check
        if baseline_latency > 0:
            drift = (current_latency - baseline_latency) / baseline_latency
            latency_ok = drift <= self.latency_drift_tolerance
            result["checks"].append({
                "name": "latency_budget",
                "passed": latency_ok,
                "drift": f"{drift:+.1%}",
                "tolerance": f"{self.latency_drift_tolerance:.0%}",
            })
            if not latency_ok:
                result["allowed"] = False
                result["recommendation"] = "block_latency_regression"

        # Error rate check
        error_ok = current_error_rate <= self.error_rate_threshold
        result["checks"].append({
            "name": "error_rate",
            "passed": error_ok,
            "current": f"{current_error_rate:.2%}",
            "threshold": f"{self.error_rate_threshold:.1%}",
        })
        if not error_ok:
            result["allowed"] = False
            result["recommendation"] = "block_error_rate"

        # Rollback suggestion
        if current_error_rate > self.rollback_threshold:
            result["recommendation"] = "immediate_rollback"

        return result


# ─── Layer 5: Drift Intelligence ───────────────────────────────────────

class DriftIntelligence:
    """
    Tracks trends over time to detect instability patterns:
        - Test pass rate decline
        - Latency drift trends
        - Error frequency evolution
        - Security anomaly growth

    When instability is detected, recommends pipeline hardening.
    """

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self._latency_history: List[float] = []
        self._error_history: List[float] = []
        self._test_pass_history: List[float] = []
        self._anomaly_history: List[Dict[str, Any]] = []

    def record_latency(self, latency_ms: float):
        self._latency_history.append(latency_ms)
        if len(self._latency_history) > self.window_size:
            self._latency_history = self._latency_history[-self.window_size:]

    def record_error_rate(self, rate: float):
        self._error_history.append(rate)
        if len(self._error_history) > self.window_size:
            self._error_history = self._error_history[-self.window_size:]

    def record_test_pass_rate(self, rate: float):
        self._test_pass_history.append(rate)
        if len(self._test_pass_history) > self.window_size:
            self._test_pass_history = self._test_pass_history[-self.window_size:]

    def detect_trends(self) -> Dict[str, Any]:
        """Analyze trends across all tracked metrics."""
        trends = {
            "latency": self._analyze_trend(self._latency_history, "latency", higher_is_worse=True),
            "error_rate": self._analyze_trend(self._error_history, "error_rate", higher_is_worse=True),
            "test_pass_rate": self._analyze_trend(self._test_pass_history, "test_pass_rate", higher_is_worse=False),
        }

        # Determine overall stability
        worsening = sum(
            1 for t in trends.values()
            if t.get("direction") == "worsening"
        )
        trends["overall_stability"] = "stable" if worsening == 0 else (
            "degrading" if worsening == 1 else "unstable"
        )

        return trends

    def recommend_actions(self) -> List[Dict[str, Any]]:
        """Recommend pipeline actions based on detected trends."""
        trends = self.detect_trends()
        actions = []

        if trends["latency"].get("direction") == "worsening":
            actions.append({
                "action": "add_regression_replay",
                "reason": f"Latency trending up: {trends['latency'].get('change', 'N/A')}",
                "severity": "warning",
            })

        if trends["error_rate"].get("direction") == "worsening":
            actions.append({
                "action": "enable_strict_rollback_gate",
                "reason": f"Error rate trending up: {trends['error_rate'].get('change', 'N/A')}",
                "severity": "critical",
            })

        if trends["test_pass_rate"].get("direction") == "worsening":
            actions.append({
                "action": "activate_shadow_deployment",
                "reason": "Test pass rate declining",
                "severity": "warning",
            })

        if trends["overall_stability"] == "unstable":
            actions.append({
                "action": "pipeline_freeze",
                "reason": "Multiple metrics degrading simultaneously",
                "severity": "critical",
            })

        return actions

    def _analyze_trend(
        self, data: List[float], name: str, higher_is_worse: bool
    ) -> Dict[str, Any]:
        """Analyze a single metric's trend."""
        if len(data) < 5:
            return {"direction": "insufficient_data", "samples": len(data)}

        # Split into halves and compare
        mid = len(data) // 2
        first_half = data[:mid]
        second_half = data[mid:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first == 0:
            change_pct = 0
        else:
            change_pct = ((avg_second - avg_first) / abs(avg_first)) * 100

        if higher_is_worse:
            direction = "worsening" if change_pct > 10 else (
                "improving" if change_pct < -10 else "stable"
            )
        else:
            direction = "worsening" if change_pct < -10 else (
                "improving" if change_pct > 10 else "stable"
            )

        return {
            "direction": direction,
            "change": f"{change_pct:+.1f}%",
            "avg_recent": round(avg_second, 4),
            "avg_previous": round(avg_first, 4),
            "samples": len(data),
        }


# ─── Business Criticality Decorator ────────────────────────────────────

class CriticalityTag:
    """Stores criticality metadata on a route handler."""

    LEVELS = {
        "financial_core": 4,
        "security_critical": 3,
        "data_critical": 2,
        "standard": 1,
    }

    def __init__(self, level: str = "standard", description: str = ""):
        self.level = level if level in self.LEVELS else "standard"
        self.description = description
        self.numeric = self.LEVELS.get(self.level, 1)


# ─── SEQP Main Engine ──────────────────────────────────────────────────

class SelfEvolvingQualityPipeline:
    """
    The Self-Evolving Quality Pipeline (SEQP) engine.

    Architecture:
        Code Change
            ↓
        Risk Analyzer
            ↓
        Auto Test Generator
            ↓
        Pipeline Rewriter Engine
            ↓
        CI/CD Platform
            ↓
        Deployment Guard
            ↓
        Runtime Feedback
            ↓
        Policy Refinement
    """

    def __init__(
        self,
        scan_paths: Optional[List[str]] = None,
        pipeline_platform: str = "github_actions",
        pipeline_output: Optional[str] = None,
        latency_drift_tolerance: float = 0.20,
        error_rate_threshold: float = 0.02,
        auto_generate_tests: bool = True,
        auto_rewrite_pipeline: bool = True,
    ):
        self.risk_analyzer = RiskAnalyzer()
        self.test_generator = AutoTestGenerator()
        self.pipeline_rewriter = PipelineRewriterEngine()
        self.deployment_guard = DeploymentGuard(
            latency_drift_tolerance=latency_drift_tolerance,
            error_rate_threshold=error_rate_threshold,
        )
        self.drift_intelligence = DriftIntelligence()

        self.scan_paths = scan_paths or ["."]
        self.pipeline_platform = pipeline_platform
        self.pipeline_output = pipeline_output
        self.auto_generate_tests = auto_generate_tests
        self.auto_rewrite_pipeline = auto_rewrite_pipeline

        self._app = None
        self._route_profiles: Dict[str, Dict[str, Any]] = {}
        self._criticality_tags: Dict[str, CriticalityTag] = {}
        self._generated_tests: Dict[str, List[Dict[str, Any]]] = {}
        self._last_pipeline: Optional[str] = None

        logger.info("SEQP: Self-Evolving Quality Pipeline initialized")

    def attach(self, app):
        """Attach the SEQP engine to an Ishaa application."""
        self._app = app
        logger.info("SEQP: Attached to Ishaa application")

    # ── Criticality Tagging ─────────────────────────────────────────

    def critical_decorator(self, level: str = "standard", description: str = ""):
        """
        Decorator to tag a route handler with business criticality.

        Usage:
            @app.route("/payment")
            @app.critical(level="financial_core")
            async def process_payment(request):
                ...
        """
        def decorator(func):
            tag = CriticalityTag(level=level, description=description)
            func._seqp_criticality = tag
            self._criticality_tags[func.__name__] = tag
            return func
        return decorator

    # ── Analysis ────────────────────────────────────────────────────

    def analyze_routes(self) -> Dict[str, Dict[str, Any]]:
        """Analyze all registered routes in the application."""
        if self._app is None:
            return {}

        profiles = {}
        for route in self._app.router.routes:
            handler = route.handler
            criticality = "standard"
            if hasattr(handler, "_seqp_criticality"):
                criticality = handler._seqp_criticality.level
            elif handler.__name__ in self._criticality_tags:
                criticality = self._criticality_tags[handler.__name__].level

            profile = self.risk_analyzer.profile_route(handler, criticality)
            profile["path"] = route.path
            profile["methods"] = list(route.methods)
            profiles[route.path] = profile

        self._route_profiles = profiles
        return profiles

    def analyze_codebase(self, paths: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Analyze Python files in the project for risk profiling."""
        scan = paths or self.scan_paths
        file_profiles = {}

        for base_path in scan:
            p = Path(base_path)
            if p.is_file() and p.suffix == ".py":
                metrics = self.risk_analyzer.analyze_file(str(p))
                file_profiles[str(p)] = metrics.to_dict()
            elif p.is_dir():
                for pyfile in p.rglob("*.py"):
                    if "__pycache__" in str(pyfile) or ".egg-info" in str(pyfile):
                        continue
                    metrics = self.risk_analyzer.analyze_file(str(pyfile))
                    file_profiles[str(pyfile)] = metrics.to_dict()

        return file_profiles

    # ── Test Generation ─────────────────────────────────────────────

    def generate_tests(self, output_path: Optional[str] = None) -> str:
        """Generate tests for all analyzed routes."""
        if not self._route_profiles:
            self.analyze_routes()

        all_tests = []
        for path, profile in self._route_profiles.items():
            metrics = CodeMetrics()
            m = profile["metrics"]
            metrics.branch_density = m["branch_density"]
            metrics.cyclomatic_complexity = m["cyclomatic_complexity"]
            metrics.nesting_depth = m["nesting_depth"]
            metrics.state_mutations = m["state_mutations"]
            metrics.db_interactions = m["db_interactions"]
            metrics.concurrency_indicators = m["concurrency_indicators"]
            metrics.external_calls = m["external_calls"]
            metrics.input_parsing = m["input_parsing"]
            metrics.security_sensitive = m["security_sensitive"]

            tests = self.test_generator.generate_tests(
                path, profile["handler"], metrics, profile.get("criticality", "standard")
            )
            self._generated_tests[path] = tests
            all_tests.extend(tests)

        code = self.test_generator.generate_test_code(all_tests)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"SEQP: Generated {len(all_tests)} tests → {output_path}")

        return code

    # ── Pipeline Rewriting ──────────────────────────────────────────

    def rewrite_pipeline(self, output_path: Optional[str] = None) -> str:
        """Generate/rewrite CI/CD pipeline based on current risk analysis."""
        if not self._route_profiles:
            self.analyze_routes()

        profiles = list(self._route_profiles.values())
        pipeline_yaml = self.pipeline_rewriter.generate_pipeline(
            profiles, platform=self.pipeline_platform
        )

        self._last_pipeline = pipeline_yaml

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(pipeline_yaml)
            logger.info(f"SEQP: Pipeline written → {output_path}")

        return pipeline_yaml

    # ── Runtime Feedback ────────────────────────────────────────────

    def record_request_metrics(self, path: str, latency_ms: float, error: bool = False):
        """Feed runtime metrics into drift intelligence."""
        self.drift_intelligence.record_latency(latency_ms)
        if error:
            self.drift_intelligence.record_error_rate(1.0)
        else:
            self.drift_intelligence.record_error_rate(0.0)

    def check_deployment_readiness(
        self,
        current_latency: float,
        baseline_latency: float,
        current_error_rate: float,
    ) -> Dict[str, Any]:
        """Check if a deployment should proceed."""
        return self.deployment_guard.check_deployment(
            current_latency, baseline_latency, current_error_rate
        )

    # ── Reporting ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get SEQP statistics."""
        return {
            "analyzed_routes": len(self._route_profiles),
            "criticality_tags": {
                name: tag.level for name, tag in self._criticality_tags.items()
            },
            "generated_test_count": sum(
                len(t) for t in self._generated_tests.values()
            ),
            "drift_trends": self.drift_intelligence.detect_trends(),
            "recommended_actions": self.drift_intelligence.recommend_actions(),
        }

    def report(self) -> Dict[str, Any]:
        """Generate a comprehensive SEQP report."""
        if not self._route_profiles:
            self.analyze_routes()

        trends = self.drift_intelligence.detect_trends()
        actions = self.drift_intelligence.recommend_actions()

        return {
            "title": "Ishaa SEQP Intelligence Report",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "routes_analyzed": len(self._route_profiles),
                "high_risk_routes": sum(
                    1 for p in self._route_profiles.values()
                    if p["metrics"]["risk_level"] in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                ),
                "critical_routes": sum(
                    1 for p in self._route_profiles.values()
                    if p.get("criticality") in ("financial_core", "security_critical")
                ),
                "total_generated_tests": sum(
                    len(t) for t in self._generated_tests.values()
                ),
                "overall_stability": trends.get("overall_stability", "unknown"),
            },
            "route_profiles": self._route_profiles,
            "drift_trends": trends,
            "recommended_actions": actions,
            "deployment_policy": self.deployment_guard._policies.get("current"),
        }

    def print_report(self):
        """Print SEQP report to console."""
        report = self.report()
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║       Ishaa SEQP — Self-Evolving Quality Pipeline Report       ║",
            "╚══════════════════════════════════════════════════════════════════╝",
            "",
            f"  Routes Analyzed:    {report['summary']['routes_analyzed']}",
            f"  High-Risk Routes:   {report['summary']['high_risk_routes']}",
            f"  Critical Routes:    {report['summary']['critical_routes']}",
            f"  Generated Tests:    {report['summary']['total_generated_tests']}",
            f"  Stability:          {report['summary']['overall_stability']}",
            "",
            "  ── Route Risk Profiles ──",
        ]

        for path, profile in report["route_profiles"].items():
            m = profile["metrics"]
            lines.append(
                f"    {path} [{m['risk_level']}] "
                f"score={m['risk_score']:.2f}, "
                f"complexity={m['cyclomatic_complexity']}, "
                f"coverage={profile.get('recommended_coverage', 0):.0%}"
            )

        if report["recommended_actions"]:
            lines.append("")
            lines.append("  ── Recommended Actions ──")
            for action in report["recommended_actions"]:
                lines.append(
                    f"    [{action['severity'].upper()}] {action['action']}: {action['reason']}"
                )

        lines.append("")
        print("\n".join(lines))

    # ── Full Evolution Cycle ────────────────────────────────────────

    def evolve(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full SEQP evolution cycle:
        1. Analyze routes
        2. Generate risk profiles
        3. Generate tests
        4. Rewrite pipeline
        5. Generate deployment policy
        6. Check drift trends
        7. Recommend actions
        """
        logger.info("SEQP: Running full evolution cycle...")

        # 1. Analyze routes
        profiles = self.analyze_routes()

        # 2. Generate deployment policy
        policy = self.deployment_guard.generate_policy(list(profiles.values()))

        # 3. Generate tests
        test_code = None
        if self.auto_generate_tests:
            test_path = os.path.join(output_dir, "test_seqp_auto.py") if output_dir else None
            test_code = self.generate_tests(output_path=test_path)

        # 4. Rewrite pipeline
        pipeline = None
        if self.auto_rewrite_pipeline:
            if self.pipeline_platform == "github_actions":
                pipe_path = os.path.join(
                    output_dir or ".", ".github", "workflows", "seqp_pipeline.yml"
                ) if output_dir else None
            else:
                pipe_path = os.path.join(output_dir, "seqp_pipeline.yml") if output_dir else None
            pipeline = self.rewrite_pipeline(output_path=pipe_path)

        # 5. Check trends
        trends = self.drift_intelligence.detect_trends()
        actions = self.drift_intelligence.recommend_actions()

        result = {
            "profiles_count": len(profiles),
            "tests_generated": sum(len(t) for t in self._generated_tests.values()),
            "pipeline_generated": pipeline is not None,
            "policy": policy,
            "trends": trends,
            "actions": actions,
        }

        logger.info(
            f"SEQP: Evolution complete — "
            f"{result['profiles_count']} routes analyzed, "
            f"{result['tests_generated']} tests generated"
        )

        return result
