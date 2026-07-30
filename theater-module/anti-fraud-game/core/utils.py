import time
import sys
from datetime import datetime

# ------------------ 辅助函数 ------------------
def get_current_time():
    """获取当前时间，格式为 HH:MM"""
    return datetime.now().strftime("%H:%M")

def print_header():
    """打印游戏头部"""
    print("=" * 60)
    print("� 反诈骗视觉小说")
    print("=" * 60)
    print()

def slow_type(text, delay=0.03, is_user=False, is_narration=False):
    """模拟打字机效果，逐个字符输出
    is_user: 是否是用户发言
    is_narration: 是否是旁白
    """
    lines = text.split('\n')
    for line in lines:
        # 逐个字符输出
        for char in line:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        print()
    print()

def show_typing(duration=1.2):
    """显示对方正在输入...并等待"""
    print(f"{get_current_time()}")
    print("对方正在输入", end="")
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    time.sleep(duration - 0.9)
    print("\n")

def colored(text, color):
    """简单的颜色输出（支持终端）"""
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "reset": "\033[0m"
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def wait_for_input(options, allow_alert=False):
    """
    等待用户输入有效选项
    options: 可选的数字选项列表，如 ['1', '2']
    allow_alert: 是否允许输入"报警"（特殊关键词）
    """
    while True:
        try:
            choice = input("请输入选项数字: ").strip().lower()
            if allow_alert and choice == '报警':
                return '报警'
            if choice in options:
                return int(choice)
            print("无效输入，请重新选择。")
        except (KeyboardInterrupt, EOFError):
            print("\n游戏中断。")
            sys.exit(0)

# 当前章节名称，用于区分不同章节的图片文件夹
current_chapter = ""

def set_chapter(chapter_name):
    """
    设置当前章节
    chapter_name: 章节名称，如 "claim_fraud" 或 "sextortion_fraud"
    """
    global current_chapter
    current_chapter = chapter_name

def display_image(image_path):
    """
    显示图片
    image_path: 图片相对路径（不包含章节文件夹）
    """
    global current_chapter
    if current_chapter:
        full_path = f"image/{current_chapter}/{image_path}"
    else:
        full_path = f"image/{image_path}"
    print(f"[图片] {full_path}")
    # 在实际环境中，可以使用PIL库或其他方法显示图片
    # 这里只是打印图片路径作为示例
    print("───────────────────────────────────────────────")
    print("│                                          │")
    print("│             [图片显示区域]              │")
    print("│                                          │")
    print("───────────────────────────────────────────────")
    print()