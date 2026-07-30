# ------------------ 用户管理模块 ------------------
class UserManager:
    """管理用户信息和游戏状态"""
    
    def __init__(self):
        self.full_name = ""
        self.surname = ""  # 姓氏
        self.identity = ""  # 身份
        self.identity_options = {
            "1": "大学生",
            "2": "上班族",
            "3": "自由职业者",
            "4": "退休人员",
            "5": "企业主"
        }
    
    def collect_user_info(self):
        """收集用户信息"""
        print("\n" + "="*60)
        print("📋 角色设定")
        print("="*60)
        
        # 收集姓名
        while True:
            name = input("请输入您的姓名（2-4个汉字）: ").strip()
            if 2 <= len(name) <= 4 and all('\u4e00' <= char <= '\u9fff' for char in name):
                self.full_name = name
                self.surname = name[0]  # 获取姓氏
                break
            print("请输入有效的中文姓名（2-4个汉字）")
        
        # 选择性别
        print("\n请选择您的性别：")
        gender_options = {
            "1": "男",
            "2": "女",
            "3": "其他"
        }
        for key, value in gender_options.items():
            print(f"{key}. {value}")
        
        while True:
            choice = input("请输入选项数字: ").strip()
            if choice in gender_options:
                self.gender = gender_options[choice]
                break
            print("无效输入，请重新选择。")
        
        # 选择身份
        print("\n请选择您的身份：")
        for key, value in self.identity_options.items():
            print(f"{key}. {value}")
        
        while True:
            choice = input("请输入选项数字: ").strip()
            if choice in self.identity_options:
                self.identity = self.identity_options[choice]
                break
            print("无效输入，请重新选择。")
        
        print(f"\n✅ 角色设定完成：{self.full_name}，{self.gender}，{self.identity}")
        print("="*60)
        import time
        time.sleep(1)
    
    def get_formatted_name(self, honorific=True):
        """
        获取格式化后的称呼
        honorific: 是否使用敬称（先生/女士）
        """
        if honorific:
            if hasattr(self, 'gender'):
                if self.gender == '男':
                    return f"{self.surname}先生"
                elif self.gender == '女':
                    return f"{self.surname}女士"
                else:
                    return f"{self.surname}同志"
            else:
                # 后备逻辑：根据常见姓氏判断
                female_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '罗', '高', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾', '肖', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁', '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '廖', '石', '孟', '黎', '金', '秦', '史', '陶', '韦', '邱', '贾', '侯', '贺', '夏', '江', '毛', '付', '段', '郝', '方', '薛', '闫', '顾', '邹', '熊', '龚', '白', '龙', '邵', '覃', '武', '钱', '戴', '严', '莫', '孔', '向', '汤', '常', '萧', '傅', '阎', '包', '康', '伍', '施', '万', '洪', '庞', '樊', '季', '庄', '殷', '温', '倪', '翟', '申', '向', '齐', '乔', '文', '安', '易', '颜', '牛', '岳', '银', '简', '骆', '毕', '章', '鲁', '关', '葛', '柳', '俞', '聂', '蓝', '祝', '纪', '焦', '祁', '耿']
                if self.surname in female_surnames:
                    return f"{self.surname}女士"
                else:
                    return f"{self.surname}先生"
        return self.full_name
    
    def replace_placeholders(self, text):
        """
        替换文本中的占位符
        {name} -> 全名
        {surname} -> 姓氏
        {gender} -> 性别
        {identity} -> 身份
        """
        gender = getattr(self, 'gender', '')
        return text.replace("{name}", self.full_name) \
                   .replace("{surname}", self.surname) \
                   .replace("{gender}", gender) \
                   .replace("{identity}", self.identity)

# 全局用户管理器实例
user_manager = UserManager()