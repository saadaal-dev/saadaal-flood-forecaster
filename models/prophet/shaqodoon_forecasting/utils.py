import json

class Config:
    def __init__(self, **entries):
        self.__dict__.update(entries)

def load_settings(file_path):
    result_object = {}
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                
                # Exclude comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                if '=' not in line:
                    raise ValueError(f"Line '{line}' is not properly formatted.")
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Try to parse the value as int
                try:
                    value = int(value)
                except ValueError:
                    pass
                
                # Try to parse the value as float
                try:
                    value = float(value)
                except ValueError:
                    pass
                
                # Try to parse the value as JSON (for lists)
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
                
                result_object[key] = value
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except IOError:
        print(f"Error: An error occurred while reading the file '{file_path}'.")
    
    result_object = Config(**result_object)

    return result_object
