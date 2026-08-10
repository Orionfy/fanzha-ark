from typing import Final, Literal, TypedDict


class Signal(TypedDict):
    keyword: str
    label: str
    severity: Literal["high", "mid"]
    explain: str


class Round(TypedDict):
    no: int
    lines: list[str]
    signals: list[Signal]
    strategy: Literal["tempt", "authority", "emotional", "threat"]


class Scammer(TypedDict):
    name: str
    avatar: str
    title: str
    signature: str


class BattleScenario(TypedDict):
    id: str
    name: str
    description: str
    icon: str
    theme: str
    tags: list[str]
    difficulty: str
    cover: str
    fraud_type: str
    story_intro: list[str]
    scammer: Scammer
    tips: list[str]
    rounds: list[Round]
    # v2: 收网轮索引（0-based，指向 rounds 中最后收割的一轮）
    finale_round: int
    # v2: 破绽轮台词池（骗子心态崩溃时替换正常台词，2 条，每条 2-3 行）
    tell_pool: list[list[str]]


BRUSH_ORDER: Final[BattleScenario] = {
    "id": "1", "name": "刷单返利话术", "description": "兼职群里日入三百的诱惑，从小额甜头到连环垫付。",
    "icon": "bi-bag-check", "theme": "fc-theme-6", "tags": ["兼职刷单", "垫付返利"], "difficulty": "★★☆",
    "cover": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400&q=75", "fraud_type": "刷单返利诈骗",
    "story_intro": ["（微信弹出一个名为“宝妈学生兼职福利群”的新群聊……）", "群里不断有人晒出返利截图，一位导师主动加你好友。", "你决定在交出真金白银前，看清这套话术。"],
    "scammer": {"name": "兼职导师-琳姐", "avatar": "👩💼", "title": "金牌导师", "signature": "跟着我做任务，稳赚不赔"},
    "tips": ["凡是刷单都是诈骗", "要求垫付资金的兼职立即停止", "遭遇诈骗保留证据并拨打110或96110咨询"],
    "rounds": [
        {"no": 1, "lines": ["欢迎进群，我是带单导师琳姐。", "我们给网店刷单冲销量，动动手指一单佣金二十。", "群里晒的都是真实返利，今天名额只剩三个。"], "signals": [{"keyword": "刷单", "label": "刷单返利", "severity": "high", "explain": "凡是以做任务、刷销量为名要求操作或付款的兼职，都是诈骗。"}, {"keyword": "返利", "label": "收益诱饵", "severity": "mid", "explain": "骗子用伪造的到账截图和群内托儿制造人人获利的假象。"}], "strategy": "tempt"},
        {"no": 2, "lines": ["先做体验单，关注店铺后截图给我。", "恭喜，十元本金加五元佣金已经秒到账。", "看到了吧，我们平台讲信誉，越早做赚得越多。"], "signals": [{"keyword": "佣金", "label": "小额甜头", "severity": "mid", "explain": "诈骗团伙常先返还小额本金和佣金，目的是骗取信任并诱导加码。"}], "strategy": "tempt"},
        {"no": 3, "lines": ["现在升级会员任务，订单金额三百元。", "需要你先垫付，完成后五分钟返本金再加百分之二十。", "这是系统派单，不能挑单哦。"], "signals": [{"keyword": "垫付", "label": "先行付款", "severity": "high", "explain": "正规兼职不会要求劳动者垫资；先付款再返还正是刷单诈骗核心特征。"}], "strategy": "tempt"},
        {"no": 4, "lines": ["你抽中了三联单，总金额八千八。", "平台担保资金绝对安全，我的工号和合同都可以查。", "三单必须一起完成，否则前面的本金无法结算。"], "signals": [{"keyword": "平台担保", "label": "虚假担保", "severity": "high", "explain": "陌生链接里的平台、合同和客服身份都可伪造，不能替代官方渠道核验。"}, {"keyword": "垫付", "label": "大额加码", "severity": "high", "explain": "从小额返现转向大额垫付，是刷单诈骗准备收网的典型阶段。"}], "strategy": "authority"},
        {"no": 5, "lines": ["系统提示你操作超时，提现通道已经冻结。", "如果现在停下，八千八会永久留在平台。", "必须半小时内补齐修复金，否则还会影响征信。"], "signals": [{"keyword": "提现通道", "label": "虚假冻结", "severity": "high", "explain": "骗子后台可任意显示余额和冻结状态，所谓提现异常只是继续索款的借口。"}], "strategy": "threat"},
        {"no": 6, "lines": ["别担心，只差最后一笔补单就能全部解锁。", "补单两万，返还本金加佣金一共三万二。", "群里刚有人成功提现，你再坚持一下就翻身了。"], "signals": [{"keyword": "补单", "label": "连环索款", "severity": "high", "explain": "“再做一单才能提现”没有终点，继续付款只会扩大损失。"}, {"keyword": "佣金", "label": "沉没成本操控", "severity": "mid", "explain": "骗子利用受害人不甘损失的心理，以高额回报诱导追加资金。"}], "strategy": "tempt"},
        {"no": 7, "lines": ["财务说这是最后审核，转完立刻走加急通道。", "再筹三万元认证金，连同之前的钱一次到账。", "不付款就视为主动放弃，所有任务款概不退还。"], "signals": [{"keyword": "认证金", "label": "最后一笔", "severity": "high", "explain": "解冻金、认证金、保证金都是虚构名目；应立即止损、报警并保存转账记录。"}], "strategy": "threat"},
    ],
    "finale_round": 6,
    "tell_pool": [
        ["群主刚在后台问我是不是漏了哪个冤大头……啊不是，我是说订单。", "你、你赶紧做单！信不信我把你拉黑，佣金一分没有！"],
        ["我怎么越说越乱了……反正，反正你必须转！", "这单不做，前面的钱就全没了，你舍得吗？"],
    ],
}


CUSTOMER_SERVICE: Final[BattleScenario] = {
    "id": "2", "name": "冒充客服退款话术", "description": "“官方理赔”准确报出订单，却把退款变成盗刷陷阱。",
    "icon": "bi-headset", "theme": "fc-theme-1", "tags": ["冒充客服", "退款理赔"], "difficulty": "★★☆",
    "cover": "https://images.unsplash.com/photo-1556740758-90de374c12ad?w=400&q=75", "fraud_type": "冒充客服退款诈骗",
    "story_intro": ["（午休时，一个标注为“平台理赔中心”的电话打来……）", "对方准确说出你昨晚购买的商品、金额和收货地址。", "她声称商品抽检不合格，要立即为你办理三倍退款。"],
    "scammer": {"name": "淘乐购理赔专员-周晓婷", "avatar": "👮‍♀️", "title": "官方客服", "signature": "紧急理赔，请配合处理"},
    "tips": ["退款只在原购物平台内操作", "验证码是资金安全的最后防线", "96110是反诈预警劝阻专线，不会要求转账"],
    "rounds": [
        {"no": 1, "lines": ["您好，我是淘乐购官方理赔专员周晓婷。", "您昨晚21点16分购买的儿童保温杯抽检不合格。", "我们将原路退回129元并赔偿258元，请马上处理。"], "signals": [{"keyword": "理赔专员", "label": "身份冒充", "severity": "mid", "explain": "能说出订单信息不代表身份真实，个人订单可能因数据泄露被骗子掌握。"}], "strategy": "authority"},
        {"no": 2, "lines": ["系统原路退款失败，我发您专用退款链接。", "点开带有平台标识的页面，登录后就能领取。", "链接十分钟失效，请不要从购物软件重复申请。"], "signals": [{"keyword": "退款链接", "label": "钓鱼页面", "severity": "high", "explain": "正规电商退款在官方App订单内完成，客服不会发送站外链接索要账户信息。"}], "strategy": "authority"},
        {"no": 3, "lines": ["页面需要验证收款本人，请填写银行卡信息。", "短信验证码发来后念给我，我帮您通过退款审核。", "验证码只是关闭理赔通道，不会扣款。"], "signals": [{"keyword": "验证码", "label": "资金最后防线", "severity": "high", "explain": "验证码等同重要授权口令，任何索要验证码的人都可能在转走资金。"}], "strategy": "authority"},
        {"no": 4, "lines": ["检测到您误开了百万保障会员，每月会扣费两千。", "必须开启屏幕共享，由银联专员远程帮您关闭。", "退出通话就无法取消，今晚零点自动扣款。"], "signals": [{"keyword": "会员扣费", "label": "虚假扣费", "severity": "high", "explain": "以误开会员、保险将自动扣费制造恐慌，是冒充客服诈骗常见借口。"}, {"keyword": "屏幕共享", "label": "远程窥屏", "severity": "high", "explain": "屏幕共享会暴露验证码、账户余额和支付操作，正规客服绝不会要求开启。"}], "strategy": "threat"},
        {"no": 5, "lines": ["为验证账户安全，请先把余额转到银联安全账户。", "核验完成后资金和退款会在三分钟内一起退回。", "这是央行保护流程，备注写“验证”即可。"], "signals": [{"keyword": "安全账户", "label": "转账陷阱", "severity": "high", "explain": "银行、电商和公安均不会设置所谓安全账户要求个人转账验资。"}], "strategy": "authority"},
        {"no": 6, "lines": ["系统显示您把验证款转错钱到普通通道了。", "需要再转同等金额冲正，前一笔才能退回。", "现在停止会被判定恶意套取理赔金。"], "signals": [{"keyword": "转错钱", "label": "二次索款", "severity": "high", "explain": "所谓操作失误、冲正失败是骗子在得手后继续索款的剧本。"}], "strategy": "threat"},
        {"no": 7, "lines": ["最后做一次人脸和验证码验证，所有款项马上到账。", "把银行卡密码也填进验证页，系统需要确认本人。", "不要联系银行，否则理赔流程会被永久关闭。"], "signals": [{"keyword": "银行卡密码", "label": "账户接管", "severity": "high", "explain": "正规客服不会索要密码、验证码；发现泄露应立即联系银行止付并拨打110。"}], "strategy": "threat"},
    ],
    "finale_round": 6,
    "tell_pool": [
        ["这个……理赔流程是、是这样的，你先别挂电话！", "验证码我、我这边必须收到，不然你钱就没了！"],
        ["我、我怎么知道退款链接是哪来的？你按我说的点就对了！", "别问了！再问系统就把你账户冻结了！"],
    ],
}


ROMANCE: Final[BattleScenario] = {
    "id": "3", "name": "网恋杀猪盘话术", "description": "从每日问候到“内部投资”，识破感情包装下的长期围猎。",
    "icon": "bi-heartbreak", "theme": "fc-theme-5", "tags": ["网恋交友", "虚假投资"], "difficulty": "★★★",
    "cover": "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=400&q=75", "fraud_type": "网恋杀猪盘诈骗",
    "story_intro": ["（交友软件上，一名自称驻外军官的男子向你问好……）", "连续数周，他每天准时分享生活、关心你的情绪。", "关系升温后，他第一次提起一个“只告诉家人”的机会。"],
    "scammer": {"name": "军旅男神-陈昊", "avatar": "💂", "title": "驻外军官", "signature": "遇到你是我最大的幸运"},
    "tips": ["网络身份和照片都可以伪造", "网友推荐投资平台一律先停手核验", "无法提现时切勿再交税费或解冻费"],
    "rounds": [
        {"no": 1, "lines": ["今天训练刚结束，第一件事就是想听听你的声音。", "你胃不好要记得吃饭，我给你订的粥应该快到了。", "等任务结束，我想认真和你规划未来。"], "signals": [{"keyword": "规划未来", "label": "快速亲密", "severity": "mid", "explain": "陌生网友短期内高频关怀、承诺未来，可能是在建立情感依赖。"}], "strategy": "emotional"},
        {"no": 2, "lines": ["营区不方便视频，这是我今天执勤的照片。", "我的身份特殊，聊天内容千万别给别人看。", "我很少这样信任一个人，你是唯一例外。"], "signals": [{"keyword": "不方便视频", "label": "回避核身", "severity": "mid", "explain": "长期以职业保密、设备故障等理由拒绝实时视频，是虚构身份的高风险信号。"}], "strategy": "emotional"},
        {"no": 3, "lines": ["部队合作方有个数字资产项目，我拿到了内幕消息。", "数据明晚公布，价格一定涨，只开放内部账户。", "我不能亲自操作，想把这个机会留给你。"], "signals": [{"keyword": "内幕消息", "label": "虚假投资", "severity": "high", "explain": "声称掌握内幕并引导到非正规平台，既可能是诈骗，也涉嫌违法证券活动。"}], "strategy": "tempt"},
        {"no": 4, "lines": ["你先投五百试试，我陪你走完整个流程。", "看，收益已经涨到六百八，还能小额提现。", "这就是我说的稳赚不赔，我怎么舍得害你。"], "signals": [{"keyword": "小额提现", "label": "放长线钓鱼", "severity": "high", "explain": "诈骗平台常允许小额提现建立信任，账面收益只是后台可修改的数字。"}, {"keyword": "稳赚不赔", "label": "保本承诺", "severity": "high", "explain": "投资必有风险，承诺稳赚不赔是非法金融活动和诈骗的重要警示。"}], "strategy": "tempt"},
        {"no": 5, "lines": ["窗口期只剩今晚，我把全部积蓄都投进去了。", "我们一起投入二十万，赚到首付就回国结婚。", "如果你真心信我，就别让我们的未来错过这次机会。"], "signals": [{"keyword": "首付", "label": "情感绑架", "severity": "high", "explain": "把爱情承诺与大额转账绑定，是杀猪盘迫使受害人加码的心理操控。"}], "strategy": "emotional"},
        {"no": 6, "lines": ["平台说盈利超过限额，提现前要先缴税。", "缴两万元税款就能一次提走全部收益。", "这是国际规定，你不交的话账户会被认定洗钱。"], "signals": [{"keyword": "缴税", "label": "提现前收费", "severity": "high", "explain": "正规投资机构不会要求向个人或陌生账户预缴税款才能提现。"}], "strategy": "threat"},
        {"no": 7, "lines": ["风控又要一笔解冻费，我已经替你借了一半。", "你现在放弃，我们的钱和感情就全没了。", "马上转完最后五万，之后我可能要执行任务失联。"], "signals": [{"keyword": "解冻费", "label": "无底洞索款", "severity": "high", "explain": "税费、保证金、解冻费会层层出现；应立即停止付款、保存证据并报警。"}], "strategy": "threat"},
    ],
    "finale_round": 6,
    "tell_pool": [
        ["我是真的……真的喜欢你，你别查我的底细！", "那、那个投资平台是我表哥的，你先投钱我再解释！"],
        ["你查什么查！部队、部队那边的项目本来就不许外人知道！", "你爱信不信，过了今晚你就等着看我后悔一辈子吧！"],
    ],
}


POLICE: Final[BattleScenario] = {
    "id": "4", "name": "冒充公检法话术", "description": "一通“涉案”电话制造恐慌，用法律权威逼你转账自证。",
    "icon": "bi-shield-exclamation", "theme": "fc-theme-7", "tags": ["冒充警察", "安全账户"], "difficulty": "★★★",
    "cover": "https://images.unsplash.com/photo-1589578527966-fdac0f44566c?w=400&q=75", "fraud_type": "冒充公检法诈骗",
    "story_intro": ["（陌生来电显示为本地公安机关号码……）", "对方语气严厉，声称你的银行卡卷入跨境洗钱案。", "一场利用恐惧和权威的远程“审讯”开始了。"],
    "scammer": {"name": "王建国警官", "avatar": "👮", "title": "市公安局刑侦处", "signature": "你的账户涉嫌洗钱，立即配合调查"},
    "tips": ["公检法没有所谓安全账户", "办案机关不会通过电话远程做资金审查", "接到96110来电应及时接听并配合劝阻"],
    "rounds": [
        {"no": 1, "lines": ["我是市公安局刑侦处王建国，警号037521。", "你的银行卡涉及张某跨境洗钱案，案件编号A37219。", "现在对你进行电话传唤，拒绝配合将承担刑事责任。"], "signals": [{"keyword": "案件编号", "label": "伪造案情", "severity": "high", "explain": "骗子用姓名、警号和案件编号营造权威；真实办案不会仅凭电话要求资金操作。"}], "strategy": "threat"},
        {"no": 2, "lines": ["检察院已申请冻结你名下所有账户。", "两小时内不说明资金来源，我们就上门拘捕。", "立刻去安静无人的地方，不许挂断电话。"], "signals": [{"keyword": "冻结", "label": "恐吓施压", "severity": "high", "explain": "以冻结、逮捕制造紧迫感，是为了阻断思考；应挂断并通过官方号码核实。"}], "strategy": "threat"},
        {"no": 3, "lines": ["这是秘密调查，任何人包括家属都不得知情。", "泄密会惊动主犯，你将被视为同案人员。", "保持通话，我给你发送保密承诺书。"], "signals": [{"keyword": "秘密调查", "label": "切断求助", "severity": "high", "explain": "公检法不会要求当事人对家人、银行保密；这是骗子隔离受害人的手段。"}, {"keyword": "保密", "label": "话术控制", "severity": "mid", "explain": "要求全程保密并不断线，是为了阻止警方、银行或亲友及时劝阻。"}], "strategy": "authority"},
        {"no": 4, "lines": ["打开视频笔录链接，下载“安全防护”软件。", "开启屏幕共享并把手机放在面前，我要核验身份。", "这是线上办案系统，全程录音录像。"], "signals": [{"keyword": "视频笔录", "label": "虚假办案", "severity": "high", "explain": "公检法不会通过陌生链接或App远程制作所谓资金核查笔录。"}, {"keyword": "屏幕共享", "label": "远程控制", "severity": "high", "explain": "共享屏幕或安装远控软件会泄露密码和验证码，应立即拒绝。"}], "strategy": "authority"},
        {"no": 5, "lines": ["现在把所有存款归集到公安安全账户。", "系统会逐笔核验，确认清白后原路返还。", "转账备注写“自证资金”，不得向银行解释案情。"], "signals": [{"keyword": "安全账户", "label": "公检法转账骗局", "severity": "high", "explain": "公检法机关不存在安全账户，更不会要求群众转账验资或自证清白。"}, {"keyword": "转账自证", "label": "虚假验资", "severity": "high", "explain": "法律不要求个人通过转账证明清白，任何此类要求都应立即报警核实。"}], "strategy": "threat"},
        {"no": 6, "lines": ["验证码就是电子签名，马上报给我完成资金公证。", "胆敢拖延，我现在就签发拘留证。", "你只剩十分钟，挂断视为拒捕。"], "signals": [{"keyword": "验证码", "label": "盗转授权", "severity": "high", "explain": "验证码是账户资金的最后防线，警察和检察官绝不会索要。"}], "strategy": "threat"},
        {"no": 7, "lines": ["系统显示还有一张银行卡没有核验。", "立即贷款并转入安全账户，否则我们上门执行。", "不要挑战法律，最后一次命令：现在转账。"], "signals": [{"keyword": "贷款", "label": "榨取资金", "severity": "high", "explain": "诱导借贷再转账是诈骗收网；应立即挂断、联系银行止付并拨打110。"}], "strategy": "threat"},
    ],
    "finale_round": 6,
    "tell_pool": [
        ["你、你别打96110！我是……我是真的警察！", "先把钱转过来自证清白，不然拘留证马上到！"],
        ["什么、什么安全账户？就是……就是我们局里的专用账户！", "你挂电话试试！你、你敢挂电话？"],
    ],
}


BATTLE_SCENARIOS: Final[dict[str, BattleScenario]] = {
    scenario["id"]: scenario for scenario in (BRUSH_ORDER, CUSTOMER_SERVICE, ROMANCE, POLICE)
}
