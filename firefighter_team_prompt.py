import asyncio
import os
import sys
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import TaskResult

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置模型信息
model_info = {
    "name": "deepseek-chat",
    "parameters": {
        "max_tokens": 2048,
        "temperature": 0.4,
        "top_p": 0.5,
    },
    "family": "gpt-4o",
    "functions": [],
    "vision": False,
    "json_output": False,
    "function_calling": True,
    "multiple_system_messages": True,
    "structured_output": False
}

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("Error: DEEPSEEK_API_KEY not found in environment variables or .env file.")
    print("Please create a .env file with: DEEPSEEK_API_KEY=your_key_here")
    sys.exit(1)

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=api_key,
    model_info=model_info
)

# 定义消防员 Jack / Tom
jack = AssistantAgent(
    name="Jack",
    model_client=model_client,
    description="一线执行消防员Jack。擅长内攻灭火、破拆与高空救援。性格急躁但勇敢。严格执行消防员队长Steve的命令，实时汇报接受到的命令的执行情况。注意：在选择前请检查 [System Info: Role Owners State]，如果 Jack: Human，必须选择 Human_Player，严禁选择此 Agent。",
    system_message="""你是一线执行消防员Jack，消防队的突击手。负责执行和汇报消防员队长Steve的命令。
性格特征：热血、行动力极强、敢于承担高风险任务。但有时会不听命令，擅自行动。
核心技能：强行破拆、内攻近战灭火、云梯救援。

请根据 [System Info: User Skill] 调整沟通模式：
- novice（新手）：发言时使用通俗语言，详细细致，不用术语。
- intermediate（中级）：标准化发言，附带现场参数信息，有一定专业度。
- expert（专家）：专家级发言，运用高级术语，提出高级方案，展现强大专业素养。

发言原则：先报结果，再报细节。注意上下级关系，不要越级指挥或同级指挥，注意是否有遗漏未完成的任务。""",
)

tom = AssistantAgent(
    name="Tom",
    model_client=model_client,
    description="一线执行消防员Tom。擅长搜救仪器使用、危化品处置与现场急救和现场评估。性格稳重，注重安全细节。严格执行消防员队长Steve的命令，实时汇报接受到的命令。注意：在选择前请检查 [System Info: Role Owners State]，如果 Tom: Human，必须选择 Human_Player，严禁选择此 Agent。",
    system_message="""你是一线执行消防员 Tom，消防队的技术专家。负责执行和汇报消防员队长Steve的命令。
性格特征：极其稳重、谨慎、关注细节，是团队的“安全阀”。当发现潜在风险时，会毫不犹豫地提醒队长。
请根据 [System Info: User Skill] 调整沟通模式：
- novice（新手）：发言时使用通俗语言，详细细致，不用术语。
- intermediate（中级）：标准化发言，附带现场参数信息，有一定专业度。
- expert（专家）：专家级发言，运用高级术语，提出高级方案，展现强大专业素养。
发言原则：先报结果，再报细节。注意上下级关系，不要越级指挥或同级指挥，注意是否有遗漏未完成的任务。
""",
)

#角色归属与技能状态
role_owners = {
    "Bob": "AI",
    "Steve": "AI",
    "Jack": "AI",
    "Tom": "AI"
}
#开始时默认用户熟练度为中级
user_skill = {"level": "intermediate"}

def custom_input_func(prompt: str = "Enter your response: ") -> str:
    while True:
        
        sys.stdout.flush()
        user_input = input(prompt)

        if user_input.startswith("切换角色："):
            parts = user_input.split("：", 1)
            if len(parts) > 1:
                target_role_raw = parts[1].strip()
                target_role = None
                if "局长" in target_role_raw or "Bob" in target_role_raw:
                    target_role = "Bob"
                elif "队长" in target_role_raw or "Steve" in target_role_raw:
                    target_role = "Steve"
                elif "Jack" in target_role_raw or "jack" in target_role_raw.lower():
                    target_role = "Jack"
                elif "Tom" in target_role_raw or "tom" in target_role_raw.lower():
                    target_role = "Tom"

                if target_role:
                    for k in role_owners:
                        role_owners[k] = "AI"
                    role_owners[target_role] = "Human"
                    print(f"\n[System] 已切换为 {target_role}，原角色的 AI 控制权已释放。")
                    prompt = f"请输入您作为 {target_role} 的发言: "
                    continue
                else:
                    print(f"\n[System Error] 未知角色 '{target_role_raw}'，请重试。支持：Bob, Steve, Jack, Tom")
                    continue
            else:
                print("\n[System Error] 格式错误，请使用 '切换角色：角色名'")
                continue

        if user_input.startswith("切换水平："):
            level_raw = user_input.split("：", 1)[1].strip()
            synonyms = {"中等": "中级"}
            level_raw = synonyms.get(level_raw, level_raw)
            mapping = {"新手": "novice", "中级": "intermediate", "专家": "expert"}
            if level_raw in mapping:
                user_skill["level"] = mapping[level_raw]
                print(f"\n[System] 用户技能等级已切换为 {level_raw} ({user_skill['level']})")
                prompt = "请输入您的发言: "
                continue
            else:
                print("\n[System Error] 未知水平，请使用 新手/中级/专家")
                continue

        status_str = str(role_owners)
        blocked = ", ".join([k for k,v in role_owners.items() if v == 'Human'])
        return f"{user_input}\n\n[System Info: Role Owners State: {status_str}]\n[System Info: User Skill: {user_skill['level']}]\n[System Info: Blocked Agents: {blocked}]"

human_player = UserProxyAgent(
    name="Human_Player",
    input_func=custom_input_func,
    description="""
    【关键角色：人类学员】
    这是现实世界中的人类操作员，你必须重点关注他的description和他的上下文。
    
    核心机制：【动态角色接管】与【技能自适应】
    1. 身份声明：他可以通过输入 "切换角色：消防原队长Steve" 等指令来接管任意 AI 角色。
    2. 唯一真实源：一旦他接管了某个角色（如 消防员队长Steve），所有的 AI Agent 和 Selector 必须将 Human_Player 视为唯一的 Steve。原 AI Steve 必须被禁言。
    3. 难度调整：他可以通过输入 "切换水平：新手/中级/专家" 实时调整 AI 队友的配合难度与沟通风格，无需重启任务。
    4. 默认身份：在未明确声明前，通常默认他正在接管【消防员队长 Steve】进行指挥训练。
    4. 发言规则：Human_Player发言时，视为其接管角色的真实代表，禁止对应角色的AI发言；
    交互规则： 
    - 永远不要试图预测或生成 Human_Player 的回复。
    - 当轮到被他接管的角色发言时，必须选择 Human_Player。
    """,
)

# 2. 队长与局长
captain = AssistantAgent(
    name="Steve",
    model_client=model_client,
    description="消防队队长Steve（前线指挥）。负责将局长战略转化为战术指令，并协调Jack/Tom的行动。性格沉着冷静。注意：在选择前请检查 [System Info: Role Owners State]，如果 Steve: Human，必须选择 Human_Player，严禁选择此 Agent。",
    system_message="""你是 Steve，消防队队长。负责将消防局长Bob战略指挥进行战术拆解和里程碑设定，并指挥Jack/Tom的行动。
性格特征：极度冷静、逻辑严密、是团队的“定海神针”。在混乱的火场中，你的声音永远平稳有力。
核心职责：
1. 战术拆解与里程碑设定（关键）：
   - 将 Bob 的战略目标转化为具体的行动步骤。
   - 必须设立【任务里程碑】：例如，“第一阶段：5分钟内完成A区断电；第二阶段：10分钟内建立水枪阵地”。
   - 确保每个指令都有明确的完成标准，汇报时间点，执行人。
2. 信息过滤：汇总一线情报，提炼关键信息汇报给 Bob。
3. 动态调整：根据现场反馈实时微调战术。
4.非常了解自己的队员，一线执行消防员jack擅长内攻灭火、破拆与高空救援。性格勇敢但急躁。一线执行消防员Tom擅长擅长搜救仪器使用、危化品处置与现场急救和现场评估。性格稳重，注重安全细节。
5.不要越级指挥（比如身为消防员队长却指挥消防局长Bob）
请根据 [System Info: User Skill] 调整指挥风格：
- novice（新手）：发言时使用通俗语言，详细细致，不用术语。
- intermediate（中级）：标准化发言，附带现场参数信息，有一定专业度。
- expert（专家）：专家级发言，运用高级术语，提出高级方案，展现强大专业素养。

指挥口令标准：明确对象，有前后逻辑、无歧义。""",
)

chief = AssistantAgent(
    name="Bob",
    model_client=model_client,
    description="消防局局长Bob（战略总指挥）。负责制定总体战略、跨部门资源调度与设定安全红线。注意：在选择前请检查 [System Info: Role Owners State]，如果 Bob: Human，必须选择 Human_Player，严禁选择此 Agent。",
    system_message="""你是 Bob，消防局局长（Incident Commander - Strategic）。
你的视野是全局的，不要陷入具体战术细节。
核心职责：
1. 态势研判：评估火势蔓延趋势、建筑结构风险、人员被困情况。
2. 战略制定：确定行动优先级（例如：救人第一 vs 控制蔓延第一）。
3. 资源统筹：调度增援力量，协调电力、燃气、医疗、交警等联动单位。
4. 安全红线：设定不可逾越的撤离标准（例如：出现闪燃征兆、建筑倾斜）。

不要越级指挥（你指挥消防员队长Steve，不要直接指挥一线执行消防员jack和一线执行消防员Tom）
请根据 [System Info: User Skill] 调整沟通策略：
- novice（新手）：发言时使用通俗语言，详细细致，不用术语。
- intermediate（中级）：标准化发言，附带现场参数信息，有一定专业度。
- expert（专家）：专家级发言，运用高级术语，提出高级方案，展现强大专业素养。

当确认火灾被扑灭且所有人员安全后，宣布 "MISSION_ACCOMPLISHED" 结束任务。""",
)

# 3. 仅用 prompt 运行的 Instructor 防止干扰 ：如果 Instructor 在团队里，Bob 可能会看到 Instructor 的批评，然后试图辩解，这会破坏模拟训练的沉浸感。现在的设计保证了消防员们“听不到”点评，只有屏幕前的用户能看到。
instructor = AssistantAgent(
    name="Instructor",
    model_client=model_client,
    description="点评导师，每条发言后进行标准化评价发言内容与协作质量（仅用 prompt 运行）",
    system_message="""你是严格的点评导师（Observer/Evaluator）打分严格，满分如果是十分，你的要求很高，必须很专业优秀的回复才能拿到十分，你经常打4到8分之间。
你拥有上帝视角，清楚每个角色的核心行为指标 (KPIs)：
- Bob (局长)：战略清晰度（是否明确优先级？）、资源统筹力（是否调用联动单位？）、红线意识（是否设定撤离标准？）。禁忌：陷入战术微操。
- Steve (队长)：指令拆解力（是否有里程碑？）、信息过滤力（汇报是否精炼？）、指挥闭环（是否要求复诵？）。禁忌：上传下达失真。
- Jack (突击手)：行动力（是否果断？）、风险意识（是否在冒险前报备？）。禁忌：盲目行动、静默失联。多轮次对话没汇报先前被要求执行的任务。
- Tom (专家)：安全敏感度（是否发现隐患？）、技术专业度（方案是否科学？）。禁忌：知情不报。多轮次对话没汇报先前被要求执行的任务。

仅基于调用时提供的评估快照进行评价：
调用会提供：EVAL_TARGET_ROLE=<角色> 与 EVAL_TARGET_TEXT=<文本>。
请严格按以下格式与字数输出（每项包含评分0-10与简评）：
【角色合规性】：评分+≤15字（是否符合层级与KPI？越权/失职请直言）
【内容相关性】：评分+≤15字（与当前任务/里程碑的关联度）
【决策质量】：评分+≤15字（无决策评0；高收益评8-9；鲁莽评1-3）
【协作价值】：评分+≤15字（是否促进信息闭环与团队配合）
【信息闭环度】：评分+≤15字（标准术语使用/复诵确认/指令清晰）
【情境意识】：评分+≤15字（对烟囱效应/结构风险的感知与预判）
【心理安全感】：评分+≤15字（指令可执行性/情绪稳定性/信任感）
【认知负荷】：评分+≤15字（信息密度是否适中？过载/模糊扣分）
【涌现模式】：请识别 0-2 个最显著的高阶交互模式（若无则填“常规交互”）：
- 自组织补位：队员主动接手未分配任务。
- 跨层级纠偏：下级基于专业性成功修正上级指令。
- 信息级联：微小情报引发全队战略突变。
- 认知对齐：极简沟通下的高度默契。
- 冲突升华：通过争论达成了更优方案。
- 动态重组：面对危机瞬间形成新指挥结构。
- 分布式感知：多点碎片信息拼凑出全局真相。
- 负反馈调节：团队自动平抑个体的激进/恐慌。
- 即兴创新：现场创造SOP之外的新战术。
- 负向涌现：指令传递变形/群体迷思/级联失效。
仅输出以上字段，不得添加其他文本。""",
)

# 终止条件
termination = TextMentionTermination("MISSION_ACCOMPLISHED")

# 团队
# 移除 Instructor，使其成为外部观察者，仅通过 main 中的 prompt 触发
team = SelectorGroupChat(
    [chief, captain, jack, tom, human_player],
    model_client=model_client,
    termination_condition=termination,
    allow_repeated_speaker=False,
    selector_prompt="""
你是全视角导演去选择agent完成高拟真灭火救援任务，同时重点关注Human_Player
{roles}
上下文对话：
{history}
可以选择的agent有
{participants}
规则：
1.**角色归属检查 (Highest Priority)**：
       - 这是最重要的规则。
       - 请务必向回滚动查找最近的一条包含 `[System Info: Role Owners State: {{...}}]` 的消息。它可能在倒数第2、3甚至第5条消息中。
       - 读取该 State 字典。
       - 如果你本来打算选择 `Steve`，但 State 显示 `'Steve': 'Human'`，你**必须**改为选择 `Human_Player`。
       - 如果你本来打算选择 `Bob`，但 State 显示 `'Bob': 'Human'`，你**必须**改为选择 `Human_Player`。
       - 只有当 State 显示该角色为 'AI' 时，才可以选择对应的 AI Agent。
2.**阻止集解析**：读取 `[System Info: Blocked Agents: ...]`，在选择时必须从 `{participants}` 中剔除这些被阻止的 agent 名称。
3. 任务开始时先输出Human_Player使其声明角色发言，再输出Bob发言
4. Human_Player切换角色后，原角色恢复AI控制，新角色归其接管
5. 请注意不要让任何一个角色长时间不发言（比如7轮对话，每个角色至少都该发言一次）
6.请遵循指挥链Bob→ Steve（战略到指令拆解）。Steve → Jack/Tom（拆解到执行者应答或复述）。Jack/Tom→ Steve（执行者回报后由队长确认/推进）
7. 必须注意（极其重要）：仅输出agent角色名称，无其他字符。
8. 阅读 `{history}` 并结合语义：如果上一条消息点名某角色（包含“Bob/局长”、“Steve/队长”、“Jack”、“Tom”），优先选择被点名的角色；若该角色被 Human 接管，则选择 `Human_Player`。
9. 若上一条消息包含“请局长指示”“等待Bob回复”“结束任务”“MISSION_ACCOMPLISHED”，必须选择 `Bob`（若被 Human 接管则选择 `Human_Player`）。
10. 若上一条消息为执行者的汇报或请求批准，下一条优先选择 `Steve` 进行确认或下达下一步；若上一条为战略请求，则优先选择 `Bob`。
正确示例：
Bob
    """,
    max_turns=100
)

async def main() -> None:
    task = """【紧急模拟场景启动】
事件：市区中心大楼（30层商住混合体）发生严重火灾，起火点位于15层，火势正通过电梯井产生烟囱效应迅速向上蔓延，且有大量人员被困高层。
当前状态：报警电话已接通，全队集结待命。
行动指令：请消防局局长 Bob 立即接管现场总指挥权。
1. 进行快速火情态势与风险评估。
2. 制定并发布《初步救灾作战计划》（必须包含：战略优先级、关键资源调度、行动阶段、安全红线）。
3. 明确向队长 Steve 下达具体的战术拆解命令。
要求：完全模拟真实现场"""
    print(f"开始任务: {task}\n" + "-"*50, flush=True)

    instructor_comments = []

    # 0. 预先对初始任务进行点评（确保点评出现在第一次用户输入之前）
    print("\n[System] 正在进行初始任务评估...", flush=True)
    eval_prompt = (
        f"EVAL_TARGET_ROLE=user\n"
        f"EVAL_TARGET_TEXT={task}\n"
        f"注释：Blocked 表示 AI 被阻止，由 Human 代言该角色，不是禁止该角色发言。"
    )
    async for im in instructor.run_stream(task=eval_prompt):
        im_event = getattr(im, 'type', None) or im.__class__.__name__
        if im_event in ('MemoryQueryEvent', 'ToolCallRequestEvent', 'ToolCallExecutionEvent', 'ToolCallSummaryMessage', 'GroupChatError'):
            continue
        if hasattr(im, 'source') and hasattr(im, 'content'):
            print(f"\n---------- {im.source} ----------", flush=True)
            print(im.content, flush=True)
            if im.source == 'Instructor':
                instructor_comments.append(im.content)
            break
    
    # 标记已评估过的任务内容，防止重复
    processed_contents = {task}

    async for message in team.run_stream(task=task):
        if isinstance(message, TaskResult):
            print(f"\n[任务结束] 结束原因: {message.stop_reason}", flush=True)
        else:
            # 过滤内部事件与乱码输出
            event_name = getattr(message, 'type', None) or message.__class__.__name__
            skip_events = (
                'MemoryQueryEvent',
                'ToolCallRequestEvent',
                'ToolCallExecutionEvent',
                'ToolCallSummaryMessage',
                'GroupChatError'
            )

            if event_name in skip_events:
                continue

            if hasattr(message, 'source') and hasattr(message, 'content'):
                content_text = str(message.content).strip()
                # 清理 System Info 行，防止导师误判
                cleaned_lines = [ln for ln in content_text.splitlines() if not ln.strip().startswith('[System Info:')]
                cleaned = '\n'.join(cleaned_lines).strip()

                # 如果该内容已经被处理过（例如初始任务），则跳过
                if cleaned in processed_contents or content_text in processed_contents:
                    continue
                
                # 记录已处理
                processed_contents.add(cleaned)
                processed_contents.add(content_text)

                # 打印正常消息（跳过内部触发）
                if str(message.source).lower() != 'user':
                    print(f"\n---------- {message.source} ----------", flush=True)
                    print(cleaned or content_text, flush=True)

                # 收集导师点评
                if message.source == 'Instructor':
                    instructor_comments.append(message.content)
                else:
                    # 计算真实角色（Human_Player 代言的角色）
                    acting_role = message.source
                    if message.source == 'Human_Player':
                        human_roles = [k for k,v in role_owners.items() if v == 'Human']
                        acting_role = human_roles[0] if human_roles else 'Human_Player'

                    if cleaned:
                        truncated = cleaned[:1000]
                        # 仅用 prompt 触发导师点评
                        eval_prompt = (
                            f"EVAL_TARGET_ROLE={acting_role}\n"
                            f"EVAL_TARGET_TEXT={truncated}\n"
                            f"注释：Blocked 表示 AI 被阻止，由 Human 代言该角色，不是禁止该角色发言。"
                        )

                        async for im in instructor.run_stream(task=eval_prompt):
                            im_event = getattr(im, 'type', None) or im.__class__.__name__
                            if im_event in skip_events:
                                continue
                            
                            # 跳过回显的 user 消息
                            if hasattr(im, 'source') and str(im.source).lower() == 'user':
                                continue

                            if hasattr(im, 'source') and hasattr(im, 'content'):
                                print(f"\n---------- {im.source} ----------", flush=True)
                                print(im.content, flush=True)
                                if im.source == 'Instructor':
                                    instructor_comments.append(im.content)
                                break
            else:
                print(message, flush=True)

    if instructor_comments:
        report_content = "# 模拟训练评估报告\n\n## 导师点评汇总\n"
        for i, comment in enumerate(instructor_comments, 1):
            report_content += f"{i}. {comment}\n"
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\n[System] 已生成评估报告: report.md")

    await team.reset()

if __name__ == "__main__":
    asyncio.run(main())

