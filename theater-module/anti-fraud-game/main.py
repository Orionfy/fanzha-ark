import time
from core.game import run_game
from scenarios import scenarios
from core.utils import slow_type, colored

# ------------------ 主菜单 ------------------
def show_menu():
    print("\n" + "="*60)
    slow_type("📱 反诈骗视觉小说集")
    print("="*60)
    slow_type("请选择你要体验的诈骗场景：")
    
    # 显示所有可用场景
    for key, scenario_info in scenarios.items():
        print(f"{key}. {scenario_info['name']} - {scenario_info['description']}")
    
    print("0. 退出游戏")
    print("="*60)

# ------------------ 主函数 ------------------
def main():
    while True:
        show_menu()
        try:
            choice = input("请输入选项数字: ").strip()
            if choice == "0":
                slow_type("感谢体验，再见！")
                break
            elif choice in scenarios:
                scenario_info = scenarios[choice]
                print(f"\n正在加载：{scenario_info['name']}")
                time.sleep(1)
                # 根据场景名称确定章节名称
                chapter_name = ""
                if "理赔" in scenario_info['name']:
                    chapter_name = "claim_fraud"
                elif "裸聊" in scenario_info['name']:
                    chapter_name = "sextortion_fraud"
                run_game(scenario_info, chapter_name)
                # 游戏结束后返回主菜单
                input("\n按回车键返回主菜单...")
            else:
                print("无效输入，请重新选择。")
        except (KeyboardInterrupt, EOFError):
            print("\n游戏中断。")
            break

if __name__ == "__main__":
    main()
