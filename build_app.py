# build_app.py
import PyInstaller.__main__
import os
import shutil
import time
import sys


def cleanup_directories():
    """Clean up build and dist directories"""
    for directory in ['build', 'dist', 'build_files']:
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
                print(f"Cleaned up {directory} directory")
                time.sleep(1)  # Give OS time to release files
        except Exception as e:
            print(f"Warning: Could not clean {directory}: {e}")


def create_exe():
    try:
        # First cleanup any existing build files
        print("Cleaning up old build files...")
        cleanup_directories()
        time.sleep(2)  # Wait for OS to fully release files

        print("Creating build directory...")
        # Create a directory for build files
        if not os.path.exists('build_files'):
            os.makedirs('build_files')

        print("Copying files...")
        # Copy necessary files to build directory
        shutil.copy('content_extractor_gui.py', 'build_files/')
        shutil.copy('content_extractor.py', 'build_files/')
        if os.path.exists('app-icon.ico'):
            shutil.copy('app-icon.ico', 'build_files/')
        else:
            print("Warning: app-icon.ico not found, using default icon")

        print("Creating config file...")
        # Create default config file
        with open('build_files/content_extractor_config.json', 'w') as f:
            f.write('{"project_dir": "", "auto_save": true}')

        # PyInstaller command line arguments
        args = [
            'build_files/content_extractor_gui.py',
            '--onefile',
            '--windowed',
            '--name=ContentExtractor',
            '--clean',  # Add clean flag to force a clean build
            '--noconfirm',  # Don't ask for confirmation
        ]

        # Add icon if it exists
        if os.path.exists('build_files/app-icon.ico'):
            args.extend(['--icon=build_files/app-icon.ico'])

        # Add required packages
        args.extend([
            '--hidden-import=tkinter',
            '--hidden-import=requests',
            '--hidden-import=bs4',
            '--hidden-import=langchain_community',
            '--hidden-import=langchain_community.llms',
            '--hidden-import=ollama',
        ])

        # Add data files
        args.extend(['--add-data=build_files/content_extractor_config.json;.'])

        print("Starting PyInstaller build process...")
        # Run PyInstaller
        PyInstaller.__main__.run(args)

        print("\nBuild process completed!")
        print("Executable location: dist/ContentExtractor.exe")

        # Verify the executable was created
        if os.path.exists('dist/ContentExtractor.exe'):
            print("Build successful! Executable was created successfully.")
        else:
            print("Warning: Executable file was not found in dist directory!")

    except Exception as e:
        print(f"\nError during build process: {str(e)}")
        print("\nTry these steps to resolve the issue:")
        print("1. Close any running instances of ContentExtractor")
        print("2. Close your IDE or any programs using the files")
        print("3. Run the script as administrator")
        print("4. Temporarily disable antivirus")
        sys.exit(1)

    finally:
        print("\nCleaning up temporary build files...")
        try:
            # Clean up build_files directory
            if os.path.exists('build_files'):
                shutil.rmtree('build_files')
            print("Cleanup completed successfully!")
        except Exception as e:
            print(f"Warning: Could not clean up build_files: {e}")


if __name__ == "__main__":
    # Add a welcome message
    print("\nContent Extractor Build Script")
    print("============================")

    # Create executable
    create_exe()