import os
import shutil
import subprocess


def build_distribution():
    print("Building distribution files...")
    command = ['python', 'setup.py', 'sdist', 'bdist_wheel']
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if result.returncode == 0:
        print("Distribution files built successfully")
    else:
        print("Failed to build distribution files")
        print(result.stderr)
        exit(1)


def upload_to_testpypi():
    repository_url = "https://upload.pypi.org/legacy/"
    api_token = 'pypi-AgEIcHlwaS5vcmcCJDRhMzQ5MmNmLWJjNjEtNDdlNC05ZTc1LWYzM2YyMGJlMmNlYwACKlszLCJjYTI4MzM4Yy1hYTRjLTRkYzctOTk4YS00M2E3NjIyMDJmODMiXQAABiDNpT_vgAml8A49OesCYZkX6Jx9HsA54dXijVboDUu50Q'


    command = [
        'twine', 'upload',
        '--repository-url', repository_url,
        '-u', '__token__',
        '-p', api_token,
        'dist/*'
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if result.returncode == 0:
        print("Upload to PyPI successful")
    else:
        print("Upload to PyPI failed")
        print(result.stderr)
        exit(1)


def clean_up():
    print("Cleaning up generated files and directories...")
    folders_to_remove = ['dist', 'build']
    egg_info_dir = None

    for item in os.listdir('.'):
        if item.endswith('.egg-info'):
            egg_info_dir = item
            break

    folders_to_remove.append(egg_info_dir)

    for folder in folders_to_remove:
        if folder and os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Removed {folder} directory")


if __name__ == "__main__":
    try:
        clean_up()
    except:
        pass
    build_distribution()
    upload_to_testpypi()
    clean_up()
