import sys
import io

class CodeExecutor:
    """
    Sandbox environment for technical coding tests.
    Note: In production, use a dedicated containerized sandbox (e.g., Docker/Epicbox).
    """
    def execute_python(self, code: str):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        try:
            # Warning: exec is dangerous without a proper sandbox
            exec(code, {"__builtins__": None}, {})
            return {
                "success": True,
                "output": redirected_output.getvalue()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            sys.stdout = old_stdout