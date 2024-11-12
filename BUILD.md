# Building Content Extractor Executable

This guide explains how to create a standalone executable version of the Content Extractor application using PyInstaller. This allows users to run the application without installing Python or dependencies.

## Prerequisites

1. Install required Python packages:
```bash
pip install pyinstaller
pip install tkinter
pip install requests
pip install beautifulsoup4
pip install langchain-community
pip install ollama
```

## Build Process

### Option 1: Using the Build Script

1. Ensure you have the following files in your project directory:
   - `content_extractor_gui.py`
   - `content_extractor.py`
   - `build_app.py`
   - `app-icon.ico` (optional)

2. Run the build script:
```bash
python build_app.py
```

3. The script will:
   - Clean up any existing build files
   - Create necessary directories
   - Copy required files
   - Create a default configuration file
   - Run PyInstaller to create the executable
   - Clean up temporary files

### Option 2: Manual Build

If you prefer to build manually, follow these steps:

1. Create a build directory:
```bash
mkdir build_files
```

2. Copy necessary files:
```bash
cp content_extractor_gui.py build_files/
cp content_extractor.py build_files/
cp app-icon.ico build_files/ # if you have an icon
```

3. Create default config file:
```bash
echo {"project_dir": "", "auto_save": true} > build_files/content_extractor_config.json
```

4. Run PyInstaller:
```bash
pyinstaller build_files/content_extractor_gui.py \
    --onefile \
    --windowed \
    --name=ContentExtractor \
    --clean \
    --noconfirm \
    --icon=build_files/app-icon.ico \
    --hidden-import=tkinter \
    --hidden-import=requests \
    --hidden-import=bs4 \
    --hidden-import=langchain_community \
    --hidden-import=langchain_community.llms \
    --hidden-import=ollama \
    --add-data="build_files/content_extractor_config.json;."
```

## Output

The executable will be created in the `dist` directory:
- Windows: `dist/ContentExtractor.exe`
- macOS/Linux: `dist/ContentExtractor`

## Troubleshooting

If you encounter issues during the build process:

1. Close any running instances:
   - Exit Content Extractor application
   - Close your IDE or any programs using the project files
   - Close any Python processes

2. Clean build directories:
```bash
rm -rf build dist build_files
```

3. Common issues and solutions:
   - **Permission errors**: Run the script as administrator
   - **File in use**: Close all applications using project files
   - **Antivirus interference**: Temporarily disable antivirus
   - **Missing dependencies**: Verify all required packages are installed
   - **Path issues**: Ensure all required files are in the correct directory

4. Check build logs:
   - Look for error messages in the console output
   - Check the PyInstaller build log in the `build` directory

## Distribution

After successful build:

1. Test the executable:
   - Run it on a clean system
   - Verify all features work correctly
   - Check if Ollama integration works

2. Package for distribution:
   - Include the executable
   - Add a README file
   - Include any necessary documentation
   - Specify Ollama requirements

## Notes

- The executable requires Ollama to be installed and running on the target system
- The first run may take longer as Ollama initializes
- Config file will be created in the same directory as the executable
- Windows Defender or antivirus might flag the executable; you may need to add an exception

## Requirements

- Windows/macOS/Linux
- PyInstaller
- All required Python packages
- Sufficient disk space (at least 1GB for build process)
- Administrative privileges (might be required)