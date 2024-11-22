from setuptools import setup, find_packages

# Function to read the requirements.txt file
def read_requirements():
    with open('requirements.txt') as req_file:
        return req_file.read().splitlines()

setup(
    name='shaqodoon-forecasting',
    version='0.1.0',
    packages=find_packages(include=['shaqodoon_forecasting', 'shaqodoon_forecasting.*']),
    install_requires=read_requirements(),
    python_requires='>=3.8',
)
