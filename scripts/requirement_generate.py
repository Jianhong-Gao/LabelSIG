import subprocess


def generate_requirements():
    try:
        # 使用pip freeze命令获取所有依赖
        result = subprocess.check_output(['pip', 'freeze'])
        result = result.decode('utf-8')  # 将输出从字节转换为字符串

        # 将结果写入requirements.txt文件
        with open('requirements.txt', 'w') as f:
            f.write(result)

        print("requirements.txt has been generated successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")


if __name__ == '__main__':
    generate_requirements()
