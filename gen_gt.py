import json
import os
from tqdm import tqdm
import openai
import tiktoken
import requests
from get_data import get_data_list

class Gen_GT():
    def __init__(self):
        # 加载openai key
        openai.api_key = os.getenv("OPENAI_API_KEY")

    # GPT 长文档问题回答 (分割文本+每个文本单独回答)
    def send(self, prompt, text_data, chat_model="gpt-3.5-turbo", model_token_limit=8192, max_tokens=2000):
        """
        该方程可以使用GPT, 结合全部的contexts回答问题, 如果contexts超过GPT token limits, 则将contexts分割后一个个输入

        一开始先输入prompt,然后通过OpenAI API将文本数据分块发送给ChatGPT。
        如果文本数据过长, 将其分割成多个块, 然后分别发送每个块。每个块都会让GPT生成一个答案

        参数：
        - prompt (str)：用于引导模型响应的提示。
        - text_data (str)：需要包含的额外文本数据。
        - max_tokens (int, 可选)：如果文本过长，分割的chunk_size, 默认值为2000
        - model_token_limit (int, 可选)：GPT模型最大token_limit, 如果全部文本长度超过该值，则删除最先输入的文本内容，默认值为8192

        返回值：
        - list：GPT的回答。
        """

        # 将文本数据tokenize
        tokenizer = tiktoken.encoding_for_model(chat_model)
        token_integers = tokenizer.encode(text_data)

        if len(token_integers) + len(tokenizer.encode(prompt))> max_tokens:
            chunk_size = max_tokens
        else:
            chunk_size = len(token_integers)
        
        # 将文本内容根据max_tokens/chunk_size切分
        chunks = [
            token_integers[i : i + chunk_size]
            for i in range(0, len(token_integers), chunk_size)
        ]
        chunks = [tokenizer.decode(chunk) for chunk in chunks]

        # 初始化输入message, 包含问题的prompt
        responses = []
        messages = [
            {"role": "user", "content": prompt},
        ]

        # 遍历全部的片段，并结合prompt+question生成答案
        for chunk in chunks:
            messages.append({"role": "user", "content": chunk})

            # 如果全部文本长度超过该值，则删除最先输入的文本内容
            while (
                sum(len(tokenizer.encode(msg["content"])) for msg in messages)
                > model_token_limit
            ):
                messages.pop(1)  # Remove the oldest chunk

            response = openai.chat.completions.create(model=chat_model, messages=messages)
            chatgpt_response = response.choices[0].message.content.strip()
            responses.append(chatgpt_response)

        return responses

    # GPT 长文档问题回答 (合并总结多个回答，最终仅生成一个回答)
    def generate_gt(self, question, context_list, chat_model='gpt-4-turbo'):
        """
        该方程与上一个方程结合使用，用于总结全部回答并最终将200个回答缩减成一个标准答案ground_truth

        参数：
        - company_name (str)：公司名
        - question_body (str)：问题主体
        - context_list (list(str))：200个contexts列表
        - chat_model (str, 可选)：生成答案使用的GPT模型，默认为'gpt-4-turbo'

        返回值：
        - str：GPT最后生成的标准答案ground_truth。
        """

        responses_storage = []
        responses = []

        prompt_text = f'''
                        请根据给定的文档回答问题
                        如果文档中的内容可以回答问题，请全面详细地回答问题并在回答中使用资料中细节，包括例子，数据等；如果不可以回答问题，请回答不知道
                        问题: {question}                
                        请不要输出与回答问题无关的任何内容
                        '''

        # 输入context_list(200个)，每一个context都生成一个答案
        for context in tqdm(context_list, desc="初始答案生成中"):
            response=self.send(prompt=prompt_text, text_data=context, chat_model=chat_model)
            responses.append(response)

        # 循环缩减回答，最后仅输出一个回答
        print("正在循环缩减回答.....")
        while len(responses)>1:
            contents = ''
            prompt_text = f'''
                            请根据以下给定的背景资料，全面详细地回答问题，请在回答中使用资料中细节，包括例子，数据等
                            问题: {question}
                            输出格式：“答案: xxx"
                            '''

            for response in responses:
                for res in response:
                    if '不知道' in res:
                        continue
                    contents+=res

            responses = self.send(prompt=prompt_text, text_data=contents, chat_model=chat_model)

        return responses[0]

if __name__ == "__main__":  
    gen = Gen_GT()

    question_list, contexts_list, answer_list = get_data_list()
    ground_truth_list=[]

    for index, question in enumerate(question_list):
        contexts = contexts_list[index]
        answer = answer_list[index]
        print(f'Question {index+1}/{len(question_list)}')
        ground_truth = gen.generate_gt(question, contexts, chat_model='gpt-4-turbo')
        ground_truth_list.append(ground_truth)

    print(ground_truth_list)

# 东方航空（80个有用信息）
# GPT-3.5: 200个contexts生成标准答案大约用时5分30秒
# GPT-4：200个contexts生成标准答案大约用时9分钟

# 优刻得 （180个有用信息）
# GPT-4：200个contexts生成标准答案大约用时25分钟