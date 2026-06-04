from setuptools import find_packages, setup
from typing import List

HYPHEN_E_DOT = '-e .'

def get_requirements(file_path: str) -> List[str]:
    """
    This function returns a list of requirements from the requirements.txt file.
    """
    requirements = []
    try:
        with open(file_path) as file_obj:
            requirements = file_obj.readlines()
            requirements = [req.replace("\n", "") for req in requirements]

            if HYPHEN_E_DOT in requirements:
                requirements.remove(HYPHEN_E_DOT)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found.")
    
    return requirements

setup(
    name="ai_interview_assistant",
    version="0.0.1",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=get_requirements("requirements.txt")
)