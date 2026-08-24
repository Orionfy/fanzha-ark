import time

from core.utils import slow_type, show_typing, wait_for_input, print_header, display_image, set_chapter, colored

# ------------------ 主游戏循环 ------------------
def run_game(scenario_info, chapter_name=""):
    """
    运行游戏（CLI 模式）
    scenario_info: 场景元数据，包含 scenario 节点图与 endings 结局数据
    chapter_name: 章节名称，用于区分不同章节的图片文件夹
    """
    scenario = scenario_info["scenario"]
    endings_data = scenario_info.get("endings", {})

    # 设置当前章节
    if chapter_name:
        set_chapter(chapter_name)

    # 首先收集用户信息
    from core.user_manager import user_manager
    user_manager.collect_user_info()

    # 打印聊天界面头部
    print_header()

    current_node = "0"
    while True:
        node = scenario.get(current_node)
        if not node:
            print(f"错误：未找到节点 {current_node}")
            break

        # 显示内容（如果有）
        if "content" in node:
            for line in node["content"]:
                # 替换占位符
                line = user_manager.replace_placeholders(line)
                # 处理图片显示
                if line.startswith("[图片]"):
                    # 提取图片路径
                    image_path = line[4:].strip()
                    display_image(image_path)
                else:
                    # 模拟对方正在输入的效果（如果是骗子发言）
                    if "小周：" in line or "民警：" in line or "对方" in line:
                        show_typing()
                        slow_type(line, is_user=False)
                    elif "你：" in line:
                        # 用户发言
                        slow_type(line, is_user=True)
                    elif line.startswith("（") or "心想：" in line or "提示：" in line:
                        # 旁白内容
                        slow_type(line, is_user=False, is_narration=True)
                    else:
                        # 系统提示或其他内容
                        slow_type(line, is_user=False)
                    time.sleep(0.3)  # 句子间停顿
        # 处理不同类型节点
        if node["type"] == "auto":
            current_node = node["next"]
        elif node["type"] == "choice":
            # 显示选项（替换占位符）
            for line in node["content"]:
                line = user_manager.replace_placeholders(line)
                slow_type(line, is_user=False)
            # 显示选项列表（替换占位符）
            print("请选择您的回复：")
            for i, (text, target) in enumerate(node["choices"], 1):
                text = user_manager.replace_placeholders(text)
                print(f"{i}. {text}")
            # 额外提示（如果允许报警）
            if node.get("allow_alert", False):
                print("（你也可以输入'报警'来采取行动）")
            # 显示输入框
            print("┌────────────────────────────────┐")
            # 获取用户输入
            allowed_options = [str(i) for i in range(1, len(node["choices"])+1)]
            choice = wait_for_input(allowed_options, node.get("allow_alert", False))
            print("└────────────────────────────────┘")
            if choice == '报警':
                # 显示用户输入的"报警"
                slow_type("你：报警", is_user=True)
                # 报警跳转目标由场景元数据提供；为空则停留原节点
                alert_node = scenario_info.get("alert_node")
                if not alert_node:
                    print("当前场景不支持在此报警")
                else:
                    current_node = alert_node
            else:
                # 显示用户选择的选项
                selected_text = node["choices"][choice-1][0]
                # 提取选项中的文本内容（去掉数字和点）
                user_text = selected_text.split('. ', 1)[1] if '. ' in selected_text else selected_text
                slow_type(f"你：{user_text}", is_user=True)
                # 根据选项数字跳转
                current_node = node["choices"][choice-1][1]
        elif node["type"] == "ending":
            # 数据驱动结局渲染
            ending_id = node.get("ending_id")
            if ending_id and ending_id in endings_data:
                ed = endings_data[ending_id]
                print("\n" + "=" * 50)
                slow_type(f"【{ed['title']}】")
                for p in ed["paragraphs"]:
                    slow_type(p)
                print(colored(f"🏆 解锁成就：{ed['achievement']}", "yellow"))
                print("=" * 50)
            break
