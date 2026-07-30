from .claim_fraud import claim_fraud_scenario
from .sextortion_fraud import sextortion_fraud_scenario
from .ticket_fraud import ticket_fraud_scenario
from .counterfeit_fraud import counterfeit_fraud_scenario
from .pig_butcher_fraud import pig_butcher_fraud_scenario
from .brushing_fraud import brushing_fraud_scenario
from .impersonate_police_fraud import impersonate_police_fraud_scenario
from endings.claim_fraud.endings import claim_fraud_endings
from endings.sextortion_fraud.endings import sextortion_fraud_endings
from endings.ticket_fraud.endings import ticket_fraud_endings
from endings.counterfeit_fraud.endings import counterfeit_fraud_endings
from endings.pig_butcher_fraud.endings import pig_butcher_fraud_endings
from endings.brushing_fraud.endings import brushing_fraud_endings
from endings.impersonate_police_fraud.endings import impersonate_police_fraud_endings

# 情景列表（数据驱动：scenario 节点图 + endings 结局数据 + alert_node 报警跳转目标）
scenarios = {
    "1": {
        "name": "理赔诈骗",
        "description": "模拟电商理赔诈骗场景",
        "scenario": claim_fraud_scenario,
        "endings": claim_fraud_endings,
        "alert_node": "23",
        "icon": "bi-cart-x",
        "theme": "fc-theme-5",
        "tags": ["电商退款", "假冒客服"],
        "difficulty": "★★☆",
        "cover": "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=400&q=75"
    },
    "2": {
        "name": "裸聊诈骗",
        "description": "模拟裸聊+色情网站+约炮诱骗场景",
        "scenario": sextortion_fraud_scenario,
        "endings": sextortion_fraud_endings,
        "alert_node": "alert_police",
        "icon": "bi-shield-exclamation",
        "theme": "fc-theme-6",
        "tags": ["裸聊勒索", "隐私威胁"],
        "difficulty": "★★★",
        "cover": "https://images.unsplash.com/photo-1614064641938-3bbee52942c4?w=400&q=75"
    },
    "3": {
        "name": "黄牛票诈骗",
        "description": "模拟购买明星演唱会黄牛票诈骗场景",
        "scenario": ticket_fraud_scenario,
        "endings": ticket_fraud_endings,
        "alert_node": None,
        "icon": "bi-ticket-perforated",
        "theme": "fc-theme-7",
        "tags": ["演唱会", "黄牛票"],
        "difficulty": "★☆☆",
        "cover": "https://images.unsplash.com/photo-1509228627152-72ae9ae6848d?w=400&q=75"
    },
    "4": {
        "name": "假冒名牌诈骗",
        "description": "模拟购买低价化妆品、LV等大牌被骗场景",
        "scenario": counterfeit_fraud_scenario,
        "endings": counterfeit_fraud_endings,
        "alert_node": None,
        "icon": "bi-bag-x",
        "theme": "fc-theme-8",
        "tags": ["低价名牌", "假冒伪劣"],
        "difficulty": "★★☆",
        "cover": "https://images.unsplash.com/photo-1567401893414-76b7b1e5a7a5?w=400&q=75"
    },
    "5": {
        "name": "杀猪盘诈骗",
        "description": "模拟网恋投资理财杀猪盘诈骗场景",
        "scenario": pig_butcher_fraud_scenario,
        "endings": pig_butcher_fraud_endings,
        "alert_node": "alert_police",
        "icon": "bi-cash-coin",
        "theme": "fc-theme-5",
        "tags": ["网恋投资", "杀猪盘"],
        "difficulty": "★★★",
        "cover": "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=400&q=75"
    },
    "6": {
        "name": "刷单返利诈骗",
        "description": "模拟兼职刷单垫付返利诈骗场景",
        "scenario": brushing_fraud_scenario,
        "endings": brushing_fraud_endings,
        "alert_node": "alert_police",
        "icon": "bi-bag-check",
        "theme": "fc-theme-6",
        "tags": ["兼职刷单", "垫付返利"],
        "difficulty": "★★☆",
        "cover": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400&q=75"
    },
    "7": {
        "name": "冒充公检法诈骗",
        "description": "模拟假冒公安检察诈骗洗钱场景",
        "scenario": impersonate_police_fraud_scenario,
        "endings": impersonate_police_fraud_endings,
        "alert_node": "alert_police",
        "icon": "bi-shield-fill-x",
        "theme": "fc-theme-7",
        "tags": ["冒充公检法", "安全账户"],
        "difficulty": "★★★",
        "cover": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400&q=75"
    }
}
