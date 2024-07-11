import subprocess


def install_requirements(requirements_file='requirements.txt'):
    try:
        subprocess.check_call(['pip', 'install', '-r', requirements_file])
        print(f"All requirements from {requirements_file} have been successfully installed.")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while installing requirements: {e}")


if __name__ == '__main__':
    install_requirements()
