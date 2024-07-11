import os
import win32com.client

def create_shortcut(target_path, shortcut_path, icon_path):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.IconLocation = icon_path  # 指定图标路径
    shortcut.save()

def create_batch_file():
    # 获取当前脚本所在的文件夹的绝对路径
    current_folder_path = os.path.abspath(os.path.dirname(__file__))

    # 使用当前文件夹路径构造main.py的路径
    main_path = os.path.abspath(os.path.join(current_folder_path, "../main.py"))

    bat_content = f"""@echo off
start /B pythonw.exe "{main_path}"
"""

    # 直接在batch-generate文件夹中创建.bat文件
    bat_path = os.path.join(current_folder_path, "CabrSIG.bat")

    with open(bat_path, "w") as bat_file:
        bat_file.write(bat_content)

    # 将快捷方式放在batch-generate的上一级目录
    shortcut_path = os.path.abspath(os.path.join(current_folder_path, "../scripts/CabrSIG.lnk"))

    # 图标的相对路径
    icon_path = os.path.abspath(os.path.join(current_folder_path, "../resource/logo.ico"))

    # 创建快捷方式并为其设置图标
    create_shortcut(bat_path, shortcut_path, icon_path)

    print(f"CabrSIG.bat has been created at {bat_path}!")
    print(f"A shortcut for CabrSIG.bat with the logo icon has been created at {shortcut_path}!")

if __name__ == "__main__":
    create_batch_file()
