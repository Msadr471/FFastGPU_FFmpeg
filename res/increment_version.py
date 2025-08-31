# increment_version.py - Auto-increment version number and generate version_info.txt
import re
from version import NAME, VERSION, FILE_DESCRIPTION, PRODUCT_NAME, PRODUCT_VERSION, COPYRIGHT, LANGUAGE, COMPANY_NAME, INTERNAL_NAME, ORIGINAL_FILENAME

def increment_version(version):
    """Increment the version number (0.0.0.1 -> 0.0.0.2)"""
    parts = version.split('.')
    if len(parts) == 4:
        try:
            # Increment the last part (build number)
            parts[3] = str(int(parts[3]) + 1)
            return '.'.join(parts)
        except ValueError:
            pass
    return version

def update_version_file(new_version):
    """Update the version.py file with the new version"""
    with open('version.py', 'r') as f:
        content = f.read()
    
    # Update VERSION and PRODUCT_VERSION
    content = re.sub(r'VERSION = "[0-9.]+"', f'VERSION = "{new_version}"', content)
    content = re.sub(r'PRODUCT_VERSION = "[0-9.]+"', f'PRODUCT_VERSION = "{new_version}"', content)
    
    with open('version.py', 'w') as f:
        f.write(content)
    
    return new_version

def generate_version_info(version):
    """Generate the version_info.txt file"""
    version_info_content = f"""# UTF-8
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version.replace('.', ', ')}),
    prodvers=({version.replace('.', ', ')}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', '{COMPANY_NAME}'),
        StringStruct('FileDescription', '{FILE_DESCRIPTION}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{INTERNAL_NAME}'),
        StringStruct('LegalCopyright', '{COPYRIGHT}'),
        StringStruct('OriginalFilename', '{ORIGINAL_FILENAME}'),
        StringStruct('ProductName', '{PRODUCT_NAME}'),
        StringStruct('ProductVersion', '{version}')]
      )]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""
    
    with open('version_info.txt', 'w') as f:
        f.write(version_info_content)
    
    print(f"Version updated to: {version}")

if __name__ == "__main__":
    new_version = increment_version(VERSION)
    updated_version = update_version_file(new_version)
    generate_version_info(updated_version)