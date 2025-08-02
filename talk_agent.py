
from base import llm_google, State, llm_qwen, llm_kimi, llm
from get_character_full_data import SimpleDatabase  # 导入流式缓冲区

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.constants import START, END

from langgraph.checkpoint.memory import MemorySaver

from langgraph.graph import StateGraph
from typing import Literal
from generate_talks import  generate_talk,generate_diary,generate_dynamic_condition,generate_dynamic_condition_picture,generate_talk_picture
from get_memory import  DatabaseManager

db = DatabaseManager("memory_data.db")
def start_talk(state:State)->dict:
    talk_number=state.get('talk_number',0)
    talk_number=talk_number+1
    print('欢迎开始聊天')
    return {'talk_number':talk_number}

def op_memory(state:State)->dict:
    long_messages = state.get('long_messages', {})
    if len(state['short_messages'])>=400:
        short_messages=state['short_messages'][-400:]
        pop_short_messages=state['short_messages'][:-400]
        for p in pop_short_messages:
            if isinstance(p,HumanMessage) and p.content in long_messages.keys():
                long_messages.pop(p)

        return {'short_messages':short_messages,'long_messages':long_messages}
    return {'short_messages':state['short_messages'],'long_messages':long_messages}

def storage_memory_block(state:State):
    tags=db.get_all_tags(state['user_id'])
    prompt_template="""
    # 角色与目标
你是一位专业的记忆块标签生成专家。你的核心任务是深入分析用户提供的“聊天记忆”片段，并为其生成或匹配最精准的“记忆块标签”。你的目标是确保每个标签都能高度概括记忆中的一个核心事件，并且遵循特定的匹配与创建规则。

# 工作流程

1.  **深度分析**：首先，仔细阅读并完全理解`[聊天记忆]`中的所有内容。识别出其中发生的一个或多个核心事件、关键决策或重要信息点。
2.  **匹配优先**：将你分析出的核心事件与`[已有标签列表]`进行逐一比对。如果某个已有标签能够准确、完整地概括记忆中的一个事件，你必须直接沿用该标签。
3.  **按需创建**：如果在`[已有标签列表]`中找不到能够描述某个核心事件的标签，你需要为该事件创建一个全新的标签。
4.  **整合输出**：一个`[聊天记忆]`片段可能包含多个独立的事件。因此，最终的结果应该是一个包含了所有被沿用和新创建标签的列表。

# 规则与约束

1.  **新标签创建规则**：
*   **内容**：必须精准概括事件的核心内容，抓住要点。
*   **细节**：在概括的同时，要包含必要的细节，使其具有区分度。
*   **长度**：绝对不能超过20个汉字。
2.  **行为准则**：
*   **优先复用**：始终优先沿用已有的标签，这是最高指令。
*   **避免冗余**：如果一个已有标签已经覆盖了某个事件，不要再为该事件创建相似的新标签。
*   **多事件处理**：如果记忆中包含多个不相关的核心事件，需要为每个事件都匹配或创建一个标签。
3.  **输出格式**：
*   你的最终输出必须是严格的 JSON 格式。
*   JSON 对象中只包含一个键 `tags`。
*   `tags` 的值是一个字符串列表 `list[str]`。


```
# 示例

## 输入
### 聊天记忆:
```
A: 我们下个月去云南的机票订好了吗？
B: 订好了，下周五早上8点的。对了，我看到一个很有意思的咖啡庄园，要不要加到行程里？
A: 好主意！一直想去看看。那就这么定了。
```

### 已有标签列表:
```
["项目A技术方案讨论", "预定下个月去云南的机票", "周末聚餐计划"]
```

## 期望输出
```
{{
"tags": [
"预定下个月去云南的机票",
"云南行程中增加参观咖啡庄园"
]
}}
```
---
# 输入

## 聊天记忆:
{message}

## 已有标签列表:
{tags}
# 请根据以上要求开始你的工作。
    """
    prompt=ChatPromptTemplate.from_template(prompt_template)
    chain=prompt|llm_google|JsonOutputParser()
    memory_block=state['short_messages'][:100]
    generate_tags=chain.invoke({'message':memory_block,'tags':tags})
    generate_tags=generate_tags['tags']
    print(f'为该段记忆生成的记忆标签：{generate_tags}')
    db.add_memory(state['user_id'],generate_tags,memory_block)





def jude_path(state:State)->Literal['get_long_message','generate_diary','generate_dynamic_condition']:
    return state['page']

def get_long_message(state:State)->dict:
    short_messages=state['short_messages'][:-1]
    user_ask=state['short_messages'][-1]
    tags=db.get_all_tags(state['user_id'])
    prompt_template="""
    # 角色与任务

你是一个智能的记忆检索决策引擎。你的核心任务是分析用户当前的询问，并结合短期聊天记忆和已有的长期记忆标签，来判断是否需要调用长期记忆。你的决策将直接影响后续的对话流程。

# 决策规则

你必须严格遵循以下三步决策流程：

1.  **分析短期记忆**：首先，仔细分析【用户最近的询问】和【短期聊天记忆】。判断仅凭【短期聊天记忆】中的信息是否足以**完整且准确**地回答【用户最近的询问】。
    *   **如果“是”**：则无需调用长期记忆。你的任务结束，直接进入步骤 3 并输出指定结果。
    *   **如果“否”**：则进入步骤 2。

2.  **匹配长期记忆标签**：在确定短期记忆不足以回答问题后，你需要将【用户最近的询问】的**核心意图**与【长期记忆块标签列表】中的每一个标签进行语义匹配。
    *   **如果找到一个或多个高度相关的标签**：请从中选择**最匹配**的一个标签。
    *   **如果所有标签都与询问内容不相关**：则判定为无需调用长期记忆，因为没有合适的记忆可以调用。

3.  **输出结果**：根据以上决策，生成最终结果。你的输出**必须**是一个 JSON 对象，且严格遵循以下格式：

    *   **无需调用长期记忆时**（即，短期记忆已足够，或没有匹配的长期记忆标签）：
        ```json
        {{
          "tags": ""
        }}
        ```
    *   **需要调用长期记忆时**（即，短期记忆不足，且找到了匹配的标签）：
        ```json
        {{
          "tags": "最匹配的那个标签名"
        }}
        ```

# 输入信息示例
[这里将填入近期的对话历史，例如：]
用户: 我们上次聊的那个关于“阿尔法项目”的计划，你还有印象吗？
AI: 当然，我们讨论了项目的三个关键阶段，并确定了第一阶段的负责人是张伟。
用户: 对，那我们当时有没有提到预算的问题？
AI: 我们提到了预算将在下周的会议上进行初步讨论。
---

### 【用户最近的询问】
[这里将填入用户的最新问题，例如：]
我们上次聊我女儿的生日礼物，最后决定买什么了吗？


### 【长期记忆块标签列表】
[这里将填入一个字符串列表，例如：]
[
"阿尔法项目计划",
"女儿的生日礼物清单",
"日本旅行攻略",
"个人投资组合分析"
]

---

# 示例

**示例 1：短期记忆已足够**

*   **短期聊天记忆**: (同上)
*   **用户最近的询问**: 第一阶段的负责人是谁来着？
*   **长期记忆块标签列表**: (同上)
*   **决策过程**: 询问的“第一阶段负责人”在短期记忆中明确提到是“张伟”。因此，短期记忆足够回答。
*   **输出**:
    ```json
    {{
      "tags": ""
    }}
    ```

**示例 2：短期记忆不足，但长期记忆匹配**

*   **短期聊天记忆**: (同上)
*   **用户最近的询问**: 我们上次聊我女儿的生日礼物，最后决定买什么了吗？
*   **长期记忆块标签列表**: (同上)
*   **决策过程**: 短期记忆是关于“阿尔法项目”的，完全不涉及“女儿的生日礼物”。将询问与长期记忆标签列表匹配，发现 "女儿的生日礼物清单" 是最相关的标签。
*   **输出**:
    ```json
    {{
      "tags": "女儿的生日礼物清单"
    }}
    ```

**示例 3：短期记忆不足，且长期记忆不匹配**

*   **短期聊天记忆**: (同上)
*   **用户最近的询问**: 明天天气怎么样？
*   **长期记忆块标签列表**: (同上)
*   **决策过程**: 短期记忆是关于“阿尔法项目”的，无法回答天气问题。将询问与长期记忆标签列表匹配，没有一个标签与“天气”相关。
*   **输出**:
    ```json
    {{
      "tags": ""
    }}
    ```
    
    
用户的输入：
短期聊天记忆：
{short_messages}
用户最近的询问:
{user_ask}
长期记忆块标签列表:
{tags}

# 开始执行

    """
    prompt=ChatPromptTemplate.from_template(prompt_template)
    chain=prompt|llm|JsonOutputParser()
    answer=chain.invoke(
        {'short_messages':short_messages,'user_ask':user_ask,'tags':tags})
    print(answer)
    long_messages=state.get('long_messages',{})
    if isinstance(answer, dict):
        tags=answer['tags']
        if tags:
            user_ask=user_ask.content
            long_messages[user_ask]=db.get_memory(state['user_id'],tags)
    return {'long_messages': long_messages}

agent = None
checkpointer = None
def get_agent_and_checkpointer():
    global agent, checkpointer

    if agent is None:
        print("--- LAZY LOADING: Creating Agent and Checkpointer for the first time... ---")
        workflow = StateGraph(State)
        workflow.add_node(start_talk.__name__, start_talk)
        workflow.add_node(generate_diary.__name__, generate_diary)
        workflow.add_node(generate_dynamic_condition.__name__, generate_dynamic_condition)
        workflow.add_node(generate_dynamic_condition_picture.__name__, generate_dynamic_condition_picture)
        workflow.add_node(generate_talk.__name__, generate_talk)
        workflow.add_node(generate_talk_picture.__name__, generate_talk_picture)
        workflow.add_node(get_long_message.__name__, get_long_message)
        workflow.add_node(op_memory.__name__, op_memory)
        workflow.add_node(storage_memory_block.__name__, storage_memory_block)
        workflow.add_edge(START, start_talk.__name__)
        workflow.add_conditional_edges(start_talk.__name__, jude_path)
        workflow.add_edge(get_long_message.__name__, generate_talk.__name__)
        workflow.add_edge(generate_talk.__name__, generate_talk_picture.__name__)
        workflow.add_edge(generate_talk_picture.__name__, op_memory.__name__)
        workflow.add_edge(op_memory.__name__, END)
        workflow.add_edge(generate_diary.__name__, storage_memory_block.__name__)
        workflow.add_edge(generate_dynamic_condition.__name__, generate_dynamic_condition_picture.__name__)
        workflow.add_edge(generate_dynamic_condition_picture.__name__, storage_memory_block.__name__)
        workflow.add_edge(storage_memory_block.__name__, END)
        checkpointer = MemorySaver()
        agent = workflow.compile(checkpointer=checkpointer)  # Pass checkpointer correctly
        print("--- LAZY LOADING: Agent and Checkpointer created. ---")

    return agent, checkpointer
