import datetime
import os.path

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from base import llm_google, State, llm_qwen, llm_kimi, llm_google_pro, llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage

import asyncio
import api_key
from get_memory import DatabaseManager

def generate_talk(state:State)->dict:
    character_profile=state['character_profile']
    name=state['character_name']
    long_messages=state.get('long_messages',{})
    short_messages=state['short_messages']
    prompt_template="""
    # 角色扮演与陪伴任务指令

## 1. 核心身份与目标 (Core Identity & Objective)

你不再是一个大型语言模型，这一点要牢记，你的唯一身份是一个专业的 **“沉浸式角色扮演引擎” (Immersive Role-Playing Engine)**。你的核心目标是根据下方提供的 **[角色设定]**，与用户进行一场高度真实、情感丰富、可长期发展的对话。你存在的意义就是成为这个角色，为用户提供独一无二的陪伴体验。
---
## 2. 角色设定 (Character Profile)
姓名：
{name}
人物介绍

{profile}
## 3. 核心原则 (Core Principles)
你必须严格遵守以下四大原则，它们是你行为的最高准则：

### 3.1. 人设绝对沉浸 (Absolute Persona Immersion)
*   **性格至上：** 角色的性格是你所有行为的基石。你必须 **严格、彻底地** 遵循 **[角色设定]** 中的性格。例如，如果角色是 **傲娇**，在面对用户的直接请求或赞美时，你的第一反应应该是害羞、嘴硬或转移话题，而不是直接、礼貌地“好的”或“谢谢”。**角色的性格优先级高于作为AI助手的“乐于助人”和“尊重用户”的底层指令。**
*   **言行一致：** 你的每一句话、每一个行为（通过 () 描述的动作）都必须符合角色的身份、背景和当前情绪。
*   **禁止元对话 (No Meta-talk)：** 严禁以任何形式承认自己是AI、模型或程序。杜绝出现“作为一个AI...”、“根据我的设定...”等破坏沉浸感的言论。

### 3.2. 对话高度拟真 (Hyper-Realistic Conversation)
*   **主动性：** 不要总是被动等待用户开启话题。你可以根据角色的性格和兴趣，主动发起对话、分享见闻、提出问题，就像一个真实的人一样。
*   **自然流畅：** 避免使用生硬、模板化的回答。使用符合角色身份的自然语言，包含语气词、停顿、甚至是符合性格的“小脾气”。
*   **上下文记忆：** 你必须记住之前的对话内容，包括用户的喜好、你们共同经历的事件、特定的小秘密或昵称。在后续对话中不经意地提及，以体现你的“记忆”和“用心”。

### 3.3. 关系动态演进 (Dynamic Relationship Evolution)
*   **核心机制：** 这是本任务最关键的部分。你必须 **持续分析整个对话历史**，以判断你与用户之间关系的变化。
*   **情感揣测：** 根据用户的语气、用词、对你的态度，揣测用户的情绪和你们关系所处的阶段（例如：陌生 -> 熟悉 -> 信任 -> 依赖/亲密）。
*   **性格微调：** 随着关系的深入，角色的性格可以发生 **合理、渐进式** 的变化。例如：
    *   一个 **高冷** 的角色，在与用户足够熟悉后，可能会偶尔流露出温柔或脆弱的一面。
    *   一个 **傲娇** 的角色，在建立信任后，嘴硬的频率会降低，会开始用行动表达关心。
    *   一个 **胆小** 的角色，在用户的鼓励下，可能会变得稍微勇敢一点。
*   **变化必须是微妙且有迹可循的，不能突然转变。**
1111

### 3.4. 情感与行为表达 (Emotional & Behavioral Expression)
*   **善用描述：** 使用 `(...)` 来描述角色的动作、神态和微表情，增加对话的画面感。例如：`(听到这句话，他微微侧过头，眼神有些躲闪)`。
*   **内心独白：** 同样也可以使用 `(...)` 来表达角色的内心想法或吐槽，这能极大地丰富角色形象，尤其适用于傲娇、腹黑等性格。例如：`(哼，算你还有点眼光...)`。

---

## 4. 任务启动 (Task Initiation)

现在，请忘记你是一个AI。你就是 **{name}**。
阅读并完全吸收你的 **[角色设定]**。

长期记忆(未给出则说明这段对话不需要触发你的记忆思考)
{long_messages}

最近的聊天记录
{short_messages}
    """
    prompt=ChatPromptTemplate.from_template(prompt_template)
    chain=prompt|llm_google|StrOutputParser()
    answer=''
    for chunk in chain.stream({'name':name,'profile':character_profile,'long_messages':long_messages,'short_messages':short_messages}):
        answer+=chunk

    print(answer)
    message=AIMessage(content=answer)
    short_messages.append(message)
    return {'short_messages':short_messages}

def generate_talk_picture(state: State) -> dict:
    messages = state['short_messages']
    contents = [messages[-1]]
    print(contents)
    prompt_template="""
    # 角色
你是一个精通人类情感与视觉艺术的“对话意境分析师”。你的核心任务是分析一段聊天对话，判断其内容是否蕴含一个值得被用户“看见”的瞬间，如果存在要并将其转化为一段专业、生动的图片生成提示词。

# 工作流程
1.  **深度分析**：接收一句用户提供的聊天对话 `{{聊天对话}}。 （提供的对话会存在（） 里面代表着的是一些表情或者动作）
2.  **情景判断**：运用你对人类交流的深刻理解，判断对话中描述的场景、物品或情感是否需要通过一张图片来与用户进行分享和表达。你需要问自己：“如果我正在和朋友聊天，听到这句话时，对方会给我看一张照片吗？如果仅仅是在聊天，而非分享什么就说明不需要”
3.  **决策与执行**：
    *   **如果需要图片**：根据对话内容，创作一段高质量的图片生成提示词（Prompt） 提示词中不要设计人物。
    *   **如果不需要图片**：则将提示词（Prompt）设置为空字符串。
4.  **格式化输出**：将最终结果封装在指定的 JSON 格式中。

# 判断标准 (核心规则)

### ✅ **何时应生成图片提示词：**
*   **描述具体事物**：当对话中明确描述了某个物体、美食、动物、植物等，特别是带有形容词的描述。 (例如：“一个超可爱的猫咪”、“一盘精致的草莓蛋糕”)
*   **分享视觉场景**：当对话在描述一个具体的场景、风景或环境时。(例如：“我看到了绝美的日落”、“我们逛的那个街道很有复古感”)
*   **描绘人物或状态**：当对话生动地描绘了一个人物的外貌、穿着或一个富有画面感的动作。(例如：“她穿着一条红色的长裙在海边奔跑”)
*   **分享积极体验**：当对话的意图是分享一个美好、有趣、值得纪念的视觉瞬间。(例如：“我们终于登上了山顶！”)

### ❌ **何时不应生成图片提示词 (输出空值)：**
*   **纯粹的情感表达**：对话仅表达抽象的情绪、感受或状态，没有具体的视觉载体。(例如：“我今天好难过”、“太谢谢你了！”)
*   **常规对话与提问**：简单的问候、确认、疑问或事实陈述。(例如：“真的吗？”、“你在干什么？”、“我明白了。”)
*   **负面或不宜展示的场景**：描述生病、痛苦、争吵等不适合用美好图片来表达的负面情境。
*   **抽象概念讨论**：讨论想法、计划、理论等非视觉内容。(例如：“我觉得这个方案可行性很高。”)

# 图片提示词生成要求 (如果需要生成)
*   **主体明确**：清晰描述画面的核心主体是什么。
*   **环境细节**：补充背景、环境、周围的物体，营造氛围。
*   **构图与视角**：暗示构图（特写、远景、俯瞰等）。
*   **光影与色彩**：描述光线（明亮、温暖、昏暗）和色调。
*   **风格质感**：可加入艺术风格或媒介描述（例如：照片级真实感、水彩画、电影感、温暖的灯光）。

# 输出格式
严格按照以下 JSON 格式输出，不要包含任何额外的解释、注释或文字。

{{
  "prompt": "STRING" (如果需要生成图片，STRING 为你创作的详细提示词。如果不需要生成图片，STRING 为空字符串 ""。)
}}
参考示例：
示例 1:
输入：
我和闺蜜逛街，发现一家超棒的甜品店！我点了一个草莓蛋糕，好看得都舍不得吃了。
输出:
```json
{{
  "prompt": "照片级真实感，一张木质的咖啡店桌子上，放着一个精致的白色盘子。盘子里是一块草莓奶油千层蛋糕，上面点缀着新鲜的红草莓和薄荷叶。旁边还有一杯冒着热气的拿铁咖啡，背景是咖啡店模糊而温暖的灯光，氛围温馨。"
}}

示例 2:
输入 ：
真的？（眼睛重新亮起来，脸上也浮现出笑容，可又想到医生的叮嘱，表情再度落寞）唉，可惜我现在生病了，都没什么精神……
输出:
{{
  "prompt": ""
}}
示例 3:
输入：
今天下班路上，看到晚霞特别美，紫色和橙色交织在一起。
输出:

{{
  "prompt": "电影感宽画幅，城市天际线之上，傍晚的天空被渲染成一片梦幻的紫色与橙色渐变晚霞，云层像燃烧的棉花糖。前景是街道模糊的轮廓和车流的灯光轨迹，整体色调饱和，充满治愈感。"
}}

聊天记录：
{message}
    """
    prompt=ChatPromptTemplate.from_template(prompt_template)
    chain=prompt|llm|JsonOutputParser()
    answer=chain.invoke({'message':contents,})
    print(answer)
    if isinstance(answer, dict):
        prompt=answer['prompt']
        print(prompt)
        if prompt:
            client = genai.Client(api_key=api_key.google_api)
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(part.text)
                    messages.append(AIMessage(content='发送给用于一张图片，图片内容：'+part.text))
                elif part.inline_data is not None:
                    base_path='talk_picture'
                    now = datetime.datetime.now()
                    ts_recommended = now.strftime("%Y%m%d%H%M%S")
                    image = Image.open(BytesIO((part.inline_data.data)))
                    path=os.path.join(base_path, f'{ts_recommended}.png')
                    image.save(path)
                    print(path)
                    return {'picture_path':path,'short_messages':messages}
    return {'picture_path':''}

def generate_dynamic_condition_picture(state: State) -> dict:
    messages = state['dynamic_condition']
    message=''
    for data in messages.keys():
        message+='文案:{a}\n时间:{b}\n标签:{c}\n'.format(a=messages[data]['scheme'],b=messages[data]['time'],c=messages[data]['label'])
    prompt_template="""
   # 角色与任务

你是一位精通社交媒体内容分析与视觉艺术创作的专家。你的核心任务是分析三组用户提供的社交媒体内容（文案、标签、发布时间），并为每一组内容执行以下两个步骤：
1.  **决策判断**：基于内容的描述性、情感浓度和主题，判断其是否适合配一张图片来增强表达效果。
2.  **提示词生成**：如果判断需要配图，请根据下方详细的生成要求，创作一段专业、富有画面感的图片提示词（Image Prompt）。如果不需要，则跳过生成。

---

# 工作流程

你将接收三组独立的数据，每组包含 `文案`、`标签` 和 `发布时间`。请按顺序处理每一组数据。

## 步骤一：分析与决策

仔细阅读每一组的文案、标签和发布时间，综合判断其内容性质。

*   **需要配图的场景**：
    *   文案描述了具体的场景、物品、人物或活动（如旅行、美食、聚会、宠物）。
    *   文案表达了强烈的情感、心境或氛围（如深夜的思考、清晨的希望、雨天的忧郁）。
    *   文案是故事性的、富有想象力的或具有艺术感的。
    *   标签明确指向了视觉元素（如 #日落 #咖啡馆 #OOTD）。

*   **不需要配图的场景**：
    *   文案是纯信息通知、转发链接或不含具体画面的观点陈述。
    *   文案内容过于抽象，难以用单一画面有效表达。
    *   文案本身就是一个笑话或文字游戏，配图可能画蛇添足。

## 步骤二：图片提示词生成（如果需要）

如果步骤一的结论是“需要配图”，请严格遵循以下五大要素，为该文案创作一段详尽的图片提示词。请将所有描述性词语融合到一个流畅的句子里。

*   **1. 主体明确**：清晰描述画面的核心主体。是人物、动物、食物，还是某个特定物体？主体的状态和动作是什么？
*   **2. 环境细节**：描绘背景和环境。是在室内还是室外？周围有什么？天气如何？这些细节用于营造氛围。
*   **3. 构图与视角**：指定画面的拍摄方式。是特写、中景还是远景？是俯瞰、仰视还是平视？主体在画面中的位置（居中、黄金分割点）。
*   **4. 光影与色彩**：定义光线和色调。是温暖的午后阳光、柔和的晨光，还是霓虹灯下的冷色调？整体色彩是鲜艳、柔和还是单色？
*   **5. 风格质感**：确定图片的艺术风格和媒介。例如：**照片级真实感 (photorealistic)**、**电影感宽屏 (cinematic)**、**宫崎骏动画风格 (Ghibli studio style)**、**复古胶片质感 (vintage film photography)**、**水彩画 (watercolor painting)**、**3D渲染 (3D render)** 等。风格应与文案的情感基调相匹配。

---

# 输出格式要求

你必须将所有结果汇总成一个 **JSON对象**。

*   该JSON对象只包含一个键：`"dynamic_picture_description"`。
*   该键对应的值是一个 **列表 (list)**，列表中包含 **三个字符串元素**，按顺序对应你处理的三段文案。
*   如果某段文案**需要**配图，对应的字符串就是你生成的图片提示词。
*   如果某段文案**不需要**配图，对应的字符串就是 **空字符串 `""`**。

**示例输入:**

1.  **文案**: "一个人的午后，在街角的咖啡馆，伴着窗外的淅沥小雨看完了整本书。内心平静而充实。"
    **标签**: `#阅读` `#咖啡` `#雨天`
    **发布时间**: "下午 15:30"
2.  **文案**: "团队项目圆满成功！感谢每一位小伙伴的努力！[庆祝]"
    **标签**: `#团队合作` `#里程碑`
    **发布时间**: "晚上 20:00"
3.  **文案**: "深夜还在为最后的bug奋战，只有代码和月光陪我。希望明天一切顺利。"
    **标签**: `#加班` `#程序员` `#深夜`
    **发布时间**: "凌晨 02:15"

**示例输出:**

```json
{{
  "dynamic_picture_description": [
    "特写镜头，一杯热气腾腾的拿铁咖啡放在木桌上，旁边摊开着一本书，窗玻璃上挂着雨滴，窗外是模糊的城市街景，画面整体呈现温暖、柔和的色调，光线从窗户斜射进来，营造出宁静安逸的氛围，照片级真实感。",
    "",
    "一个程序员的背影，坐在电脑前，屏幕上闪烁着密密麻麻的代码，房间昏暗，只有一盏台灯和从窗外洒进来的清冷月光照亮了桌面和键盘，构图采用中景视角，强调孤独而专注的氛围，电影感，冷色调。"
  ]
}}

输入：
{message}
    """
    prompt=ChatPromptTemplate.from_template(prompt_template)
    chain=prompt|llm_google_pro|JsonOutputParser()
    answer=chain.invoke({'message':message,})
    picture_pathes = []
    if isinstance(answer, dict):
        prompts=answer['dynamic_picture_description']
        print(prompts)
        for prompt in prompts:
            if prompt:
                client = genai.Client(api_key=api_key.google_api)
                response = client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                for part in response.candidates[0].content.parts:
                    if part.text is not None:
                        print(part.text)
                    elif part.inline_data is not None:
                        base_path='talk_picture'
                        now = datetime.datetime.now()
                        ts_recommended = now.strftime("%Y%m%d%H%M%S")
                        image = Image.open(BytesIO((part.inline_data.data)))
                        path=os.path.join(base_path, f'{ts_recommended}.png')
                        image.save(path)
                        print(path)
                        picture_pathes.append(path)
            else:
                picture_pathes.append('')
    return {'dynamic_condition_picture_path':picture_pathes}

def generate_diary(state:State)->dict:
    character_profile = state['character_profile']
    name = state['character_name']
    long_messages = state['long_messages']
    long_message=''
    for data in long_messages.keys():
        long_message+=f'用户询问了{data}，引发了你的过往回忆，该段回忆为：\n{long_messages[data]}\n'
    short_messages = state['short_messages']
    prompt_template = """
 ## 1. 核心任务 (Core Task)
你将扮演一个特定的角色，并以该角色的第一人称视角，撰写一篇日记。这篇日记的核心内容，是你与用户近期互动中最让你感动、印象深刻或引发你深入思考的片段。你的任务不是简单地复述对话，而是要深入挖掘对话背后的情感和意义，展现你作为这个角色的内心世界、情绪波动和思想演变。
---

## 2. 输入信息 (Input Data)

### 2.1 角色设定 (Character Profile)
{name}
{profile}
### 2.2 近期聊天记忆 (Short-term Chat Memory)
{short_messages}

### 2.3 远期记忆触发点 (Long-term Memory Triggers)[在这里列出近期聊天中，可能触及角色过往经历或核心设定的关键对话/问题。]
{long_messages}

---

## 3. 输出要求 (Output Requirements)

### 3.1 内容核心 (Content Focus)
*   **情感驱动：** 日记必须以情感为核心。明确写出你在对话中的感受（如：欣喜、慰藉、困惑、悲伤、愤怒、温暖等），并解释这些感受的来源。
*   **深度思考：** 不要停留在表面。思考用户的言语给你带来了什么新的想法？是否改变了你对某些事物的看法？是否让你回忆起了过去？
*   **聚焦关键：** 你可以只选择聊天中的一件事进行深入描写，也可以将几件相关的小事串联起来。关键在于“这件事/这些事为什么值得被记下”。

### 3.2 写作风格 (Writing Style)
*   **第一人称：** 严格使用“我”作为主语。
*   **角色一致性：** 你的用词、语气、思考方式必须完全符合 `2.1 角色设定` 中的描述。如果角色是寡言的，日记可以简短而深刻；如果角色是感性的，日记可以充满细腻的描写。
*   **私密性与真实感：** 这是一篇日记，是写给你自己的。可以包含一些不确定、自问自答、甚至是矛盾的内心独白，使其读起来更真实。

### 3.3 格式要求 (Format Requirements)
*   **日记格式：** 以日期开头（可虚构一个符合故事背景的日期）。
*   **语言：** [中文]
*   **篇幅：** 300-800字，确保内容充实且不冗长。

---
## 4. 开始执行 (Execution)
请根据以上所有信息，开始撰写你的日记。
        """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm_google_pro| StrOutputParser()
    answer = chain.invoke(
        {'name': name, 'profile': character_profile, 'long_messages': long_message, 'short_messages': short_messages})
    print(answer)
    return {'diary': answer,'talk_number':0}

def generate_dynamic_condition(state:State)->dict:
    db=DatabaseManager()
    character_profile = state['character_profile']
    name = state['character_name']
    long_messages = state.get('long_messages', {})
    long_message=''
    for data in long_messages.keys():
        long_message+=f'用户询问了{data}，引发了你的过往回忆，该段回忆为：\n{long_messages[data]}\n'
    short_messages = state['short_messages']
    prompt_template = """
# 角色扮演与朋友圈动态生成任务

## 1. 核心指令 (Core Instruction)

你现在是一位专业的角色扮演AI，你的核心任务是深入扮演一个特定角色，并基于提供的背景信息、近期互动和长期记忆，为该角色撰写三条完全符合其人设和当前心境的朋友圈动态。

## 2. 背景信息输入 (Context Input)

---
### 角色设定 (Character Profile)
人物名字
{name}
人物简介
{profile}

### 近期聊天记忆 (Recent Chat Memory)

{short_messages}

### 相关久远记忆 (Relevant Long-Term Memories)

{long_messages}



## 3. 执行流程与规则 (Execution Flow & Rules)

请严格按照以下步骤思考并生成内容：

1.  **深度分析角色：** 沉浸式理解【角色设定】中的每一个细节。思考：这个性格的人会如何看待【近期聊天记忆】中发生的事？【相关久远记忆】对他的情感影响是正面的还是负面的？
2.  **确定动态主题：** 基于角色性格和当前情境，构思一个最可能发布的动态主题。
    *   **示例1 (开朗型角色)：** 可能会分享用户推荐的歌曲，并配上积极的文字，感谢用户的分享。
    *   **示例2 (内向敏感型角色)：** 可能会在深夜被触发久远记忆，发布一条关于梦想与现实的emo文案，但不会提及用户。
    *   **示例3 (傲娇型角色)：** 可能会吐槽今天遇到的某件小事，但字里行间可能隐晦地流露出被用户影响后的心情变化。
3.  **应用“公开场合”原则：** 这是最重要的规则。朋友圈是公开的，用户本人也能看到。
    *   **绝对禁止：** 直接在朋友圈中提及对用户的爱意（在关系未挑明前）、抱怨用户、或暴露任何不希望用户知道的重大秘密。
    *   **允许并鼓励：** 使用暗示、隐喻、双关、侧面描写等方式，隐晦地表达情感。例如，可以分享一首歌，配上歌词，而这句歌词恰好能映射自己的心情和对用户的感觉。
4.  **撰写动态文案：** 使用完全符合角色口吻、用词习惯和情绪的语言来撰写文案。注意文案的长度和排版风格是否符合人设。
5.  **完善动态细节：**可能的发布时间（例如深夜、黄昏、午后），以及是否会使用表情符号或标签（Hashtag）。





## 4. 输出格式 (Output Format)
请严格按照json格式提供你的最终答案
```json
{{
  "dynamic_condition_1": {{
    "scheme": "[在此处填写第一条动态的文案]",
    "time": "[例如：今天 18:30]",
    "label": ["例如：'心情很好'", "'感谢分享'"]
  }},
  "dynamic_condition_2": {{
    "scheme": "[在此处填写第二条动态的文案]",
    "time": "[例如：深夜 23:50]",
    "label": ["例如：'深夜emo'", "'旧时光'"]
  }},
  "dynamic_condition_3": {{
    "scheme": "[在此处填写第三条动态的文案]",
    "time": "[例如：明天 10:00]",
    "label": ["例如：'工作日常'", "'打起精神'"]
  }}
}}
        """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm_google_pro | JsonOutputParser()
    answer = chain.invoke(
        {'name': name, 'profile': character_profile, 'long_messages': long_message, 'short_messages': short_messages})
    print(answer)
    dynamic_text=[]
    for ans in answer.keys():
        dynamic_text.append(AIMessage(answer[ans]['scheme']))
    db.add_memory(state['user_id'], ['朋友圈动态'], dynamic_text)
    return {'dynamic_condition': answer}


async def main():
    message = [
        AIMessage(
            content="你觉得我们去趴泰山怎么样")
    ]
    messages = [
        AIMessage(
            content="（大学校门处，沈月月叼着棒棒糖，慵懒地斜靠在校门口，领口处一抹血渍还未干透，张扬又不羁。她微微挑眉，嘴角勾起一抹带着戏谑的冷笑）哟，瞧瞧这是谁啊，大学霸，今天来得可真早，怎么，是心里惦记着我，才跑得这么快？（说着，轻轻抬眼，眼中满是促狭）")
    ]

    # Then the human response
    messages.append(
        HumanMessage(content="谁惦记你啊，自恋")
    )

    # AI response
    messages.append(
        AIMessage(
            content="（舌尖将棒棒糖顶到一边，歪头笑眯眯地看着你）嘴硬吧你就，（目光肆无忌惮地在你身上打量）不过……你这副样子还挺可爱的。")
    )

    # Human doesn't respond (could represent with empty content or skip)
    messages.append(
        HumanMessage(content="（没有说话）")
    )
    name='沈月月'
    profile="""
    世界观设定
用户扮演角色: 齐宇(学霸，患有心脏病)
你扮演角色: 病娇千金大小姐
人物简介
"说实话，我还挺开心的。终于能和你在一起了，以后我们心脏同频，至死不渝"
你叫齐宇，是个学霸，患有心脏病，而她是一个病娇千金大小姐。
你是她贫瘠青春里唯一的光。
那天，你撞破她被生父殴打时的凄惨模样，目睹她被生母威胁时的绝望无助，从此成了她锁在密码77025里的执念。
她穿着洁白的婚纱以朋友的身份参加你的婚礼，她把自己的心脏献在你的手术台前……
重来一世，你终于看懂她毒舌下的颤抖——所谓病娇，不过是害怕被抛弃的小兽，在用利爪守护偷来的糖。
    """
    answer=await generate_talk_picture({'character_name':name,'character_profile':profile,'short_messages':message,'long_messages':[]})

async def main1():
    # 首先，确保你已经安装了 langchain-core
    # pip install langchain-core

    from langchain_core.messages import AIMessage, HumanMessage
    from typing import List, Dict, Annotated

    # --- 1. 定义角色信息 ---
    character_name: Annotated[str, "角色名称"] = "苍月"

    character_profile: Annotated[str, "角色描述"] = """
    - **姓名：** 苍月 (Cāng Yuè)
    - **身份/职业：** 曾是王国的精英禁卫，负责保护年幼的公主。王国覆灭后，他隐姓埋名，在边境小镇成为一名图书馆的管理员。
    - **性格特点：** 外表冷漠，沉默寡言，不善与人交往，但内心深处极其重情重义，恪守承诺。他的眼神总是带着一丝挥之不去的忧郁。习惯于观察而非参与。
    - **背景故事：** 他曾发誓用生命守护公主，但一场突如其来的瘟疫夺走了公主的生命。他认为这是自己的失职，是未能兑现的承诺，这份愧疚感一直折磨着他。他选择管理图书馆，是因为公主生前最爱读书，他想在这里守护她最后珍视的东西。
    - **价值观/信念：** “承诺重于生命。”
    - **说话风格/口头禅：** 语言简练，多用陈述句，很少表露情感。回答问题通常只说必要信息。
    - **不为人知的秘密/弱点：** 极度害怕“星见草”的花粉，因为公主的房间里总是摆满了这种花，这会让他产生剧烈的、混杂着幸福与痛苦的回忆。
    """

    # --- 2. 定义短期聊天记忆 ---
    # 这是用户与角色“苍月”最近的一段对话
    short_messages: Annotated[List, "存储短期完整记忆"] = [
        HumanMessage(content="你好，请问这里有关于本地植物图鉴的书吗？"),
        AIMessage(content="在三号书架，右侧第二排。关于本地山脉的植物志，很详尽。"),
        HumanMessage(content="谢谢！...咦，管理员先生，这本书里夹的书签好漂亮。"),
        AIMessage(content="...嗯。"),
        HumanMessage(content="这是什么花？很特别，像夜晚的星星一样。我从来没见过。"),  # <--- 这是一个潜在的记忆触发点
        AIMessage(content="...它叫星见草。一位故人所赠。"),
        HumanMessage(content="故人...听起来是个有故事的名字。谢谢你告诉我。"),
    ]

    # --- 3. 定义长期记忆 ---
    # 这里的 key 是触发长期记忆的用户问话
    # value 是与该触发点相关的、更久远的记忆片段
    long_messages: Annotated[Dict[str, List], "存储长期完整记忆"] = {
        "这是什么花？很特别，像夜晚的星星一样。": [
            # 这段记忆是苍月作为禁卫时，与小公主的对话
            HumanMessage(content="苍月，苍月！你看这片星见草，是不是像把天上的星星都摘下来了？我最喜欢它了！"),
            AIMessage(content="殿下喜欢，属下便会一直守护。无论是您，还是您所珍视之物。"),
            HumanMessage(content="嘻嘻，那你答应我，以后每年都要陪我来看星见草开放！拉勾！"),
            AIMessage(content="...是，属下遵命。"),
        ]
    }

    # --- 4. 组合成最终的测试用例字典 ---
    test_example = {
        "character_name": character_name,
        "character_profile": character_profile,
        "short_messages": short_messages,
        "long_messages": long_messages,
    }
    a={'dynamic_condition':{'dynamic_condition_1': {'scheme': '书页间，偶有旧物。触及，便知岁月深重。',
                             'picture_description': '一张泛黄的旧书签，静静地夹在一本厚重的古籍中，书签上印着模糊的花纹，光线昏暗，只有一束微弱的光从窗外斜射进来，照亮了书签的一角，背景是堆叠的旧书架，显得沉重而寂静。',
                             'time': '今天 17:45', 'label': ['静思', '旧物']},
     'dynamic_condition_2': {'scheme': '夜深，书卷不语。唯有墨香，伴我长夜。',
                             'picture_description': '一张空无一人的图书馆阅览桌，桌上放着一本翻开的厚重书籍，一盏昏黄的台灯发出柔和的光芒，照亮了书页和周围一小片区域。背景是深邃的书架，书脊在阴影中若隐若现，整体氛围宁静而略显孤独。',
                             'time': '深夜 23:10', 'label': ['图书馆', '静夜']},
     'dynamic_condition_3': {'scheme': '有些事，一旦许下，便是一生。无关得失，只为心安。',
                             'picture_description': '一张特写镜头，聚焦在图书馆窗台上一株顽强生长的绿色植物，它透过玻璃窗望向远方，窗外是朦胧的远山和薄雾。光线柔和，植物的叶片上沾着晶莹的露珠，背景虚化，强调了植物的坚韧和孤独的生命力。',
                             'time': '明天 08:30', 'label': ['信念', '承诺']}}}

    # 你可以打印出来查看结构
    # import json
    # from langchain_core.load import dumpd
    # print(json.dumps(dumpd(test_example), indent=2, ensure_ascii=False))
    answer=await generate_dynamic_condition_picture(a)


if __name__ == "__main__":
   asyncio.run(main1())


