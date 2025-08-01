from typing import TypedDict, List, Annotated
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
import api_key

class State(TypedDict):
    short_messages: Annotated[list, "存储短期完整记忆"]
    long_messages: Annotated[dict, "存储长期完整记忆"]
    character_profile: Annotated[str, "角色描述"]
    character_name:Annotated[str, "角色名称"]
    diary:Annotated[str, "日记内容"]
    dynamic_condition:Annotated[dict, "朋友圈动态"]
    picture_path:Annotated[str, "聊天图片路径"]
    dynamic_condition_picture_path:Annotated[list[str], "朋友圈动态图片路径"]
    page:Annotated[str, "所处阶段"]
    talk_number:Annotated[int, "对话次数"]
    user_id:Annotated[str, "用户id"]

llm_google = ChatOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key.google_api,
    model="gemini-2.5-flash",
    temperature=0.8,
    streaming=True,
)
llm_google_pro = ChatOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key.google_api,
    model="gemini-2.5-pro",
    temperature=0.7,
    streaming=True,
)

llm_qwen=ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=api_key.qwen_api,
    model="qwen-max-latest",
    temperature=0.5,
    streaming=True,
)
llm_kimi=ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=api_key.qwen_api,
    model="Moonshot-Kimi-K2-Instruct",
    temperature=0.7,
    streaming=True,
)
llm=ChatOpenAI(
    base_url="https://api.deepseek.com",
    api_key=api_key.dp_api,
    model="deepseek-chat",
    temperature=0.7,
    streaming=True,
) ##deepseek_v3
